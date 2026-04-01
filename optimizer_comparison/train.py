"""
Adam vs Muon optimizer comparison on California Housing regression.

Usage:
    python optimizer_comparison/train.py --optimizer adam --learning_rate 0.003 --seed 0
    python optimizer_comparison/train.py --optimizer muon --learning_rate 0.01 --seed 42 --epochs 200
"""

import argparse
import os

import numpy as np
import torch
import torch.nn as nn
from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
from torch.utils.data import DataLoader, TensorDataset

import wandb


class RegressionMLP(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def build_optimizer(model, optimizer_name, lr):
    """Build optimizer. For Muon, uses torch.optim.Muon on 2D+ weight matrices
    and a separate Adam for biases/batchnorm params (Muon only works on >=2D tensors)."""
    if optimizer_name == "adam":
        return [torch.optim.Adam(model.parameters(), lr=lr)]

    if optimizer_name == "muon":
        muon_params = [p for p in model.parameters() if p.ndim >= 2]
        other_params = [p for p in model.parameters() if p.ndim < 2]
        optimizers = [torch.optim.Muon(muon_params, lr=lr, weight_decay=0.01)]
        if other_params:
            optimizers.append(torch.optim.Adam(other_params, lr=lr, weight_decay=0.01))
        return optimizers

    raise ValueError(f"Unknown optimizer: {optimizer_name}")


def load_data(batch_size, seed):
    data = fetch_california_housing()
    X, y = data.data, data.target

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=seed
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)

    train_ds = TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32),
    )
    val_ds = TensorDataset(
        torch.tensor(X_val, dtype=torch.float32),
        torch.tensor(y_val, dtype=torch.float32),
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    return train_loader, val_loader


def train_one_epoch(model, loader, optimizers, criterion):
    model.train()
    total_loss = 0.0
    n_batches = 0
    for X_batch, y_batch in loader:
        for opt in optimizers:
            opt.zero_grad()
        preds = model(X_batch)
        loss = criterion(preds, y_batch)
        loss.backward()
        for opt in optimizers:
            opt.step()
        total_loss += loss.item()
        n_batches += 1
    return total_loss / n_batches


@torch.no_grad()
def evaluate(model, loader, criterion):
    model.eval()
    total_loss = 0.0
    n_batches = 0
    all_preds, all_targets = [], []
    for X_batch, y_batch in loader:
        preds = model(X_batch)
        total_loss += criterion(preds, y_batch).item()
        n_batches += 1
        all_preds.append(preds.numpy())
        all_targets.append(y_batch.numpy())

    avg_loss = total_loss / n_batches
    all_preds = np.concatenate(all_preds)
    all_targets = np.concatenate(all_targets)
    r2 = r2_score(all_targets, all_preds)
    return avg_loss, r2


def parse_args():
    parser = argparse.ArgumentParser(description="Adam vs Muon on California Housing")
    parser.add_argument("--optimizer", choices=["adam", "muon"], required=True)
    parser.add_argument("--learning_rate", type=float, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=64)
    return parser.parse_args()


def main():
    args = parse_args()

    # Reproducibility
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # W&B — reads project/entity/run_name/group from env vars (set by sweep skill)
    wandb.init(
        project=os.environ.get("WANDB_PROJECT", "adam-vs-muon"),
        entity=os.environ.get("WANDB_ENTITY", "hiremath-sujai1"),
        name=os.environ.get("WANDB_RUN_NAME", f"{args.optimizer}_lr{args.learning_rate}_s{args.seed}"),
        group=os.environ.get("WANDB_RUN_GROUP", "default"),
        config={
            "optimizer": args.optimizer,
            "learning_rate": args.learning_rate,
            "seed": args.seed,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "model": "MLP-256-128-64",
            "dataset": "california_housing",
        },
    )

    train_loader, val_loader = load_data(args.batch_size, args.seed)
    model = RegressionMLP(input_dim=8)
    optimizers = build_optimizer(model, args.optimizer, args.learning_rate)
    criterion = nn.MSELoss()

    print(f"Training: optimizer={args.optimizer}, lr={args.learning_rate}, seed={args.seed}")

    best_val_r2 = -float("inf")

    for epoch in range(args.epochs):
        train_loss = train_one_epoch(model, train_loader, optimizers, criterion)
        val_loss, val_r2 = evaluate(model, val_loader, criterion)

        best_val_r2 = max(best_val_r2, val_r2)

        wandb.log({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_mse": val_loss,
            "val_r2": val_r2,
            "best_val_r2": best_val_r2,
        })

        if (epoch + 1) % 20 == 0:
            print(f"  Epoch {epoch+1}/{args.epochs} — train_loss={train_loss:.4f}, val_r2={val_r2:.4f}")

    print(f"Done. Best val R²: {best_val_r2:.4f}")
    wandb.finish()


if __name__ == "__main__":
    main()

"""
Analyze Adam vs Muon sweep results from W&B.

Pulls all runs from the sweep, generates charts and summary tables.
Charts are saved as PNGs for terminal display via kitty icat.

Usage:
    python optimizer_comparison/analyze.py
"""

import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import wandb

ENTITY = "hiremath-sujai1"
PROJECT = "adam-vs-muon"
GROUP = "adam-vs-muon"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "plots")


def fetch_runs():
    """Pull all sweep runs from W&B."""
    api = wandb.Api()
    runs = list(api.runs(f"{ENTITY}/{PROJECT}", filters={"group": GROUP}))
    print(f"Fetched {len(runs)} runs from W&B")
    return runs


def parse_run_name(name):
    """Parse trial-N-optimizer-lrX-sY format."""
    # e.g. "trial-3-adam-lr0.01-s2"
    import re
    m = re.match(r"trial-(\d+)-(\w+)-lr([\d.]+)-s(\d+)", name)
    if m:
        return m.group(2), float(m.group(3)), int(m.group(4))
    return None, None, None


def extract_summaries(runs):
    """Extract config and final metrics from each run."""
    records = []
    for r in runs:
        if r.state != "finished":
            continue
        optimizer, lr, seed = parse_run_name(r.name)
        records.append({
            "name": r.name,
            "optimizer": optimizer,
            "lr": lr,
            "seed": seed,
            "best_val_r2": r.summary.get("best_val_r2"),
            "final_train_loss": r.summary.get("train_loss"),
            "final_val_loss": r.summary.get("val_loss"),
            "runtime_s": r.summary.get("_wandb", {}).get("runtime", None),
        })
    return records


def fetch_histories(runs, keys=("train_loss", "val_loss", "val_r2")):
    """Pull per-epoch history for each run. Returns dict keyed by (optimizer, lr, seed)."""
    histories = {}
    for r in runs:
        if r.state != "finished":
            continue
        opt, lr, seed = parse_run_name(r.name)
        hist = r.history(keys=list(keys), pandas=False)
        histories[(opt, lr, seed)] = hist
    print(f"Fetched histories for {len(histories)} runs")
    return histories


def plot_loss_curves(histories):
    """Plot averaged train/val loss curves per (optimizer, lr), with std shading."""
    # Group by (optimizer, lr)
    grouped = defaultdict(list)
    for (opt, lr, seed), hist in histories.items():
        grouped[(opt, lr)].append(hist)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    colors = {"adam": "#2196F3", "muon": "#FF5722"}

    for ax, metric, title in [(axes[0], "train_loss", "Train Loss"), (axes[1], "val_loss", "Val Loss")]:
        for (opt, lr), hists in sorted(grouped.items()):
            # Align epochs and compute mean/std
            arrays = []
            for h in hists:
                vals = [row[metric] for row in h if metric in row and row[metric] is not None]
                arrays.append(vals)
            min_len = min(len(a) for a in arrays)
            arrays = [a[:min_len] for a in arrays]
            arr = np.array(arrays)
            mean = arr.mean(axis=0)
            std = arr.std(axis=0)
            epochs = np.arange(min_len)

            label = f"{opt} lr={lr}"
            linestyle = "-" if opt == "adam" else "--"
            ax.plot(epochs, mean, label=label, color=colors[opt], linestyle=linestyle,
                    alpha=0.6 + 0.3 * (lr == 0.003))
            ax.fill_between(epochs, mean - std, mean + std, alpha=0.08, color=colors[opt])

        ax.set_xlabel("Epoch")
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Adam vs Muon: Loss Curves (mean ± std across seeds)", fontsize=13)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "loss_curves.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Saved: {path}")
    return path


def plot_r2_curves(histories):
    """Plot R² curves per (optimizer, lr)."""
    grouped = defaultdict(list)
    for (opt, lr, seed), hist in histories.items():
        grouped[(opt, lr)].append(hist)

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"adam": "#2196F3", "muon": "#FF5722"}
    alpha_map = {0.01: 1.0, 0.003: 0.7, 0.001: 0.4}

    for (opt, lr), hists in sorted(grouped.items()):
        arrays = []
        for h in hists:
            vals = [row["val_r2"] for row in h if "val_r2" in row and row["val_r2"] is not None]
            arrays.append(vals)
        min_len = min(len(a) for a in arrays)
        arrays = [a[:min_len] for a in arrays]
        arr = np.array(arrays)
        mean = arr.mean(axis=0)
        std = arr.std(axis=0)
        epochs = np.arange(min_len)

        linestyle = "-" if opt == "adam" else "--"
        ax.plot(epochs, mean, label=f"{opt} lr={lr}", color=colors[opt],
                linestyle=linestyle, alpha=alpha_map.get(lr, 0.7))
        ax.fill_between(epochs, mean - std, mean + std, alpha=0.08, color=colors[opt])

    ax.set_xlabel("Epoch")
    ax.set_ylabel("Val R²")
    ax.set_title("Adam vs Muon: Validation R² Over Training")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "r2_curves.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Saved: {path}")
    return path


def plot_r2_boxplot(records):
    """Box plot of best val R² per (optimizer, lr) group."""
    grouped = defaultdict(list)
    for r in records:
        grouped[(r["optimizer"], r["lr"])].append(r["best_val_r2"])

    labels = []
    data = []
    colors_list = []
    for key in sorted(grouped.keys()):
        opt, lr = key
        labels.append(f"{opt}\nlr={lr}")
        data.append(grouped[key])
        colors_list.append("#2196F3" if opt == "adam" else "#FF5722")

    fig, ax = plt.subplots(figsize=(10, 5))
    bp = ax.boxplot(data, labels=labels, patch_artist=True, widths=0.6)
    for patch, color in zip(bp["boxes"], colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    # Overlay individual points
    for i, d in enumerate(data):
        x = np.random.normal(i + 1, 0.04, size=len(d))
        ax.scatter(x, d, alpha=0.5, s=20, color="black", zorder=3)

    ax.set_ylabel("Best Val R²")
    ax.set_title("Best Validation R² by Optimizer and Learning Rate")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "r2_boxplot.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Saved: {path}")
    return path


def plot_runtime_comparison(records):
    """Bar chart comparing wall-clock runtime per config."""
    grouped = defaultdict(list)
    for r in records:
        if r["runtime_s"] is not None:
            grouped[(r["optimizer"], r["lr"])].append(r["runtime_s"])

    if not grouped:
        print("No runtime data available, skipping runtime chart.")
        return None

    labels = []
    means = []
    stds = []
    colors_list = []
    for key in sorted(grouped.keys()):
        opt, lr = key
        labels.append(f"{opt}\nlr={lr}")
        means.append(np.mean(grouped[key]))
        stds.append(np.std(grouped[key]))
        colors_list.append("#2196F3" if opt == "adam" else "#FF5722")

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=stds, color=colors_list, alpha=0.7, capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Runtime (seconds)")
    ax.set_title("Wall-Clock Runtime per Trial (mean ± std)")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "runtime.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Saved: {path}")
    return path


def print_summary_table(records):
    """Print a formatted summary table."""
    grouped = defaultdict(list)
    for r in records:
        grouped[(r["optimizer"], r["lr"])].append(r)

    print("\n" + "=" * 70)
    print("  SWEEP RESULTS: Adam vs Muon on California Housing")
    print("=" * 70)
    print(f"  {'Config':<20} {'Best R² (mean±std)':<22} {'Train Loss':<14} {'Val Loss':<14} {'N':>3}")
    print("-" * 70)

    rows = []
    for key in sorted(grouped.keys()):
        opt, lr = key
        runs = grouped[key]
        r2s = [r["best_val_r2"] for r in runs if r["best_val_r2"] is not None]
        tls = [r["final_train_loss"] for r in runs if r["final_train_loss"] is not None]
        vls = [r["final_val_loss"] for r in runs if r["final_val_loss"] is not None]

        label = f"{opt} lr={lr}"
        r2_str = f"{np.mean(r2s):.4f} ± {np.std(r2s):.4f}" if r2s else "N/A"
        tl_str = f"{np.mean(tls):.4f}" if tls else "N/A"
        vl_str = f"{np.mean(vls):.4f}" if vls else "N/A"
        print(f"  {label:<20} {r2_str:<22} {tl_str:<14} {vl_str:<14} {len(runs):>3}")
        rows.append((label, np.mean(r2s) if r2s else 0, r2s))

    print("-" * 70)

    # Best config
    best = max(rows, key=lambda x: x[1])
    print(f"\n  Best config: {best[0]} (R² = {best[1]:.4f})")

    # Head-to-head at each LR
    print("\n  Head-to-head (Adam vs Muon at same LR):")
    lrs = sorted(set(r["lr"] for r in records))
    for lr in lrs:
        adam_r2 = [r["best_val_r2"] for r in records if r["optimizer"] == "adam" and r["lr"] == lr and r["best_val_r2"] is not None]
        muon_r2 = [r["best_val_r2"] for r in records if r["optimizer"] == "muon" and r["lr"] == lr and r["best_val_r2"] is not None]
        if adam_r2 and muon_r2:
            adam_mean, muon_mean = np.mean(adam_r2), np.mean(muon_r2)
            winner = "Adam" if adam_mean > muon_mean else "Muon"
            diff = abs(adam_mean - muon_mean)
            print(f"    lr={lr}: Adam={adam_mean:.4f}, Muon={muon_mean:.4f} -> {winner} wins by {diff:.4f}")

    print("=" * 70)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Fetch data
    runs = fetch_runs()
    records = extract_summaries(runs)
    print(f"  {len(records)} finished runs")

    # Summary table
    print_summary_table(records)

    # Fetch histories for curve plots
    print("\nFetching per-epoch histories (this takes a minute)...")
    histories = fetch_histories(runs)

    # Generate plots
    print("\nGenerating charts...")
    plots = []
    plots.append(plot_loss_curves(histories))
    plots.append(plot_r2_curves(histories))
    plots.append(plot_r2_boxplot(records))
    plots.append(plot_runtime_comparison(records))

    print(f"\nAll plots saved to {OUTPUT_DIR}/")
    print("Display with: kitty +kitten icat <path>")

    # Return paths for display
    return [p for p in plots if p is not None]


if __name__ == "__main__":
    main()

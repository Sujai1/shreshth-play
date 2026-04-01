"""Quick test to verify W&B integration works."""
import random
import wandb

run = wandb.init(
    entity="hiremath-sujai1",
    project="test-setup",
    config={
        "learning_rate": 0.02,
        "architecture": "CNN",
        "dataset": "CIFAR-100",
        "epochs": 10,
    },
)

for epoch in range(1, 11):
    offset = random.random() / 5
    acc = 1 - 2**-epoch - random.random() / epoch - offset
    loss = 2**-epoch + random.random() / epoch + offset
    run.log({"acc": acc, "loss": loss, "epoch": epoch})

run.finish()
print("W&B test passed! Check your project at https://wandb.ai/hiremath-sujai1/test-setup")

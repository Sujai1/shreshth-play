import time
import random


def load_data(path):
    """Simulate loading a dataset."""
    print(f"Loading data from {path}...")
    time.sleep(1)
    data = [random.gauss(0, 1) for _ in range(1000)]
    print(f"Loaded {len(data)} samples")
    return data


def compute_loss(predictions, targets):
    """Mean squared error."""
    assert len(predictions) == len(targets)
    total = 0
    for pred, tgt in zip(predictions, targets):
        total += (pred - tgt) ** 2
    return total / len(predictions)


def train_model(data, learning_rate=0.01, epochs=5):
    """Train a toy model."""
    weight = random.random()
    bias = random.random()

    for epoch in range(epochs):
        predictions = [weight * x + bias for x in data]
        targets = [0.5 * x + 0.3 for x in data]
        loss = compute_loss(predictions, targets)

        # Gradient descent (simplified)
        weight -= learning_rate * (weight - 0.5)
        bias -= learning_rate * (bias - 0.3)

        print(f"Epoch {epoch+1}/{epochs} | Loss: {loss:.6f} | Weight: {weight:.4f} | Bias: {bias:.4f}")
        time.sleep(0.5)

    print("Training complete!")
    return weight, bias


def save_model(weight, bias, path="model.txt"):
    """Save model weights to file."""
    with open(path, "w") as f:
        f.write(f"weight={weight}\nbias={bias}\n")
    print(f"Model saved to {path}")


if __name__ == "__main__":
    data = load_data("data/train.csv")
    weight, bias = train_model(data, learning_rate=0.01, epochs=5)
    save_model(weight, bias)

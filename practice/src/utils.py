import os
import json
from datetime import datetime


def read_config(config_path):
    """Read a JSON config file."""
    with open(config_path, "r") as f:
        config = json.load(f)
    return config


def setup_logging(log_dir="logs"):
    """Create log directory and return a log file path."""
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"run_{timestamp}.log")
    return log_path


def format_metrics(metrics_dict):
    """Format a dictionary of metrics into a readable string."""
    parts = []
    for key, value in metrics_dict.items():
        if isinstance(value, float):
            parts.append(f"{key}: {value:.4f}")
        else:
            parts.append(f"{key}: {value}")
    return " | ".join(parts)


def validate_data(data):
    """Check data is a non-empty list of numbers."""
    if not isinstance(data, list):
        raise TypeError(f"Expected list, got {type(data)}")
    if len(data) == 0:
        raise ValueError("Data is empty")
    for i, item in enumerate(data):
        if not isinstance(item, (int, float)):
            raise TypeError(f"Item {i} is {type(item)}, expected number")
    return True


def compute_statistics(data):
    """Compute basic statistics on a list of numbers."""
    validate_data(data)
    n = len(data)
    mean = sum(data) / n
    sorted_data = sorted(data)
    median = sorted_data[n // 2] if n % 2 == 1 else (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
    variance = sum((x - mean) ** 2 for x in data) / n
    std = variance ** 0.5
    return {
        "count": n,
        "mean": mean,
        "median": median,
        "std": std,
        "min": min(data),
        "max": max(data),
    }

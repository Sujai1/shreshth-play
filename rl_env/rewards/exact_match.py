"""
Exact-match accuracy reward.

Returns 1.0 if the predicted answer matches the ground truth, 0.0 otherwise.
This is the canonical reward for math/reasoning tasks (DeepSeek-R1, GRPO paper).

Training dynamics you'll observe with accuracy-only reward:
  - Very sparse signal early in training (most completions wrong)
  - Once the model finds the right format, reward spikes sharply
  - Risk of reward hacking: model memorizes answer without reasoning
"""


def score(predicted: str, ground_truth: str) -> float:
    """Binary: 1.0 if match, 0.0 otherwise."""
    return 1.0 if predicted.strip() == ground_truth.strip() else 0.0


def soft_score(predicted: str, ground_truth: str, tolerance: float = 0.01) -> float:
    """
    Soft numeric match — useful when small rounding differences are acceptable.
    Returns 1.0 if |pred - gt| / |gt| < tolerance, else 0.0.
    """
    try:
        pred_val = float(predicted.replace(",", "").strip())
        gt_val = float(ground_truth.replace(",", "").strip())
        if gt_val == 0:
            return 1.0 if pred_val == 0 else 0.0
        return 1.0 if abs(pred_val - gt_val) / abs(gt_val) < tolerance else 0.0
    except ValueError:
        return 0.0

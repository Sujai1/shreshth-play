"""
Format compliance reward.

Rewards the model for using the expected <think>...</think><answer>...</answer> structure.

Why format rewards matter:
  - Without them, models often produce correct answers without structured reasoning
  - The format is a proxy for the reasoning process we care about
  - Too high a format weight causes models to produce well-formatted wrong answers
  - This is a classic reward-hacking failure mode to watch for in your experiments

Training dynamics you'll observe when adding format reward:
  - Early spikes in format score as model learns to imitate the template
  - Sometimes format score rises faster than accuracy (model learns template, not reasoning)
  - Helps with consistency but can mask underlying capability gaps
"""

import re

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_ANSWER_RE = re.compile(r"<answer>.*?</answer>", re.DOTALL | re.IGNORECASE)


def score(completion: str) -> float:
    """
    Returns a score in [0, 1] based on format compliance.

    Scoring breakdown:
      0.5 points: has a <think>...</think> block
      0.5 points: has an <answer>...</answer> block
      Bonus: penalize if answer block is empty or contains no digits
    """
    has_think = bool(_THINK_RE.search(completion))
    has_answer = bool(_ANSWER_RE.search(completion))

    base_score = (0.5 * has_think) + (0.5 * has_answer)

    # Small penalty if <answer> block has no numeric content
    if has_answer:
        answer_content = _ANSWER_RE.search(completion).group(0)
        if not re.search(r"\d", answer_content):
            base_score -= 0.1

    return max(0.0, base_score)


def strict_score(completion: str) -> float:
    """
    Binary: 1.0 only if both tags are present and in the right order.
    Harsher signal — forces the model to get format exactly right.
    """
    think_match = _THINK_RE.search(completion)
    answer_match = _ANSWER_RE.search(completion)
    if not think_match or not answer_match:
        return 0.0
    # think must come before answer
    return 1.0 if think_match.start() < answer_match.start() else 0.0

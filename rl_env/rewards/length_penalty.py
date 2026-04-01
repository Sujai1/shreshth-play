"""
Length-based reward shaping.

Why length matters:
  - Without length pressure, GRPO models often produce increasingly verbose outputs
    (a known failure mode called "length hacking" or verbosity bias)
  - Too harsh a length penalty causes models to cut off their reasoning prematurely
  - A soft bell-curve reward around a target length is usually best

Training dynamics you'll observe:
  - Length reward typically rises quickly then plateaus — easy to optimize
  - If weight is too high relative to accuracy, model learns to produce
    medium-length wrong answers (reward hacking)
  - Good as a regularizer with low weight (0.05–0.15)
"""

import math


def score(completion: str, target_tokens: int = 200, tolerance: float = 0.5) -> float:
    """
    Soft bell-curve reward centered at target_tokens.

    Uses a Gaussian: reward = exp(-((len - target) / (tolerance * target))^2)
    Returns 1.0 at exactly target_tokens, decays smoothly on either side.

    Args:
        completion:    the model's output text
        target_tokens: ideal response length in tokens (approximated by words * 1.3)
        tolerance:     fraction of target that defines the half-width (default 0.5)
    """
    # Rough token count: words * 1.3 is a common approximation
    approx_tokens = len(completion.split()) * 1.3
    deviation = (approx_tokens - target_tokens) / (tolerance * target_tokens)
    return math.exp(-(deviation**2))


def hard_penalty(completion: str, min_tokens: int = 20, max_tokens: int = 500) -> float:
    """
    Binary: 0.0 if outside [min, max] token range, 1.0 otherwise.
    Simpler but creates sharp cliffs in the reward landscape.
    """
    approx_tokens = len(completion.split()) * 1.3
    return 1.0 if min_tokens <= approx_tokens <= max_tokens else 0.0

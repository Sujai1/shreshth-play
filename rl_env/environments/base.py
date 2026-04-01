"""
Base environment class — mirrors Prime Intellect's verifiers pattern.

An Environment has three parts:
  1. dataset  — iterable of {prompt, answer} dicts
  2. rubric   — one or more reward functions
  3. env      — ties them together, exposes .get_batch() and .score()

Prime Intellect verifiers: https://github.com/PrimeIntellect-ai/verifiers
"""

from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Optional
import asyncio


RewardFn = Callable[[str, str], float]
# signature: (completion: str, ground_truth: str) -> float in [0, 1]


@dataclass
class Rubric:
    """Holds one or more reward functions and combines their scores."""

    funcs: List[RewardFn]
    weights: Optional[List[float]] = None  # defaults to equal weighting

    def __post_init__(self):
        if self.weights is None:
            self.weights = [1.0 / len(self.funcs)] * len(self.funcs)
        assert len(self.funcs) == len(self.weights), "funcs and weights must have same length"
        assert abs(sum(self.weights) - 1.0) < 1e-6, "weights must sum to 1"

    def score(self, completion: str, answer: str) -> Dict[str, float]:
        """
        Returns per-reward-function scores and the weighted total.
        Each reward fn may be sync or async.
        """
        scores = {}
        for fn, w in zip(self.funcs, self.weights):
            # Support both sync and async reward functions
            if asyncio.iscoroutinefunction(fn):
                raw = asyncio.run(fn(completion, answer))
            else:
                raw = fn(completion, answer)
            scores[fn.__name__] = raw

        total = sum(scores[fn.__name__] * w for fn, w in zip(self.funcs, self.weights))
        scores["total"] = total
        return scores


@dataclass
class SingleTurnEnv:
    """
    Simplest possible RL environment:
      - one prompt in, one completion out
      - no multi-turn, no tool calls, no state
    This matches the setting used in DeepSeek-R1 / GRPO papers.
    """

    dataset: List[Dict[str, Any]]  # list of {"prompt": str, "answer": str}
    rubric: Rubric

    def get_batch(self, indices: List[int]) -> List[Dict[str, Any]]:
        """Return a batch of (prompt, answer) pairs by index."""
        return [self.dataset[i] for i in indices]

    def score_completion(self, completion: str, answer: str) -> Dict[str, float]:
        """Score a single completion against its ground truth answer."""
        return self.rubric.score(completion, answer)

    def score_batch(
        self, completions: List[str], answers: List[str]
    ) -> List[Dict[str, float]]:
        """Score a batch of completions. Returns list of score dicts."""
        if len(completions) != len(answers):
            raise ValueError(
                f"completions and answers must have the same length, "
                f"got {len(completions)} and {len(answers)}"
            )
        return [self.rubric.score(c, a) for c, a in zip(completions, answers)]

    def __len__(self):
        return len(self.dataset)

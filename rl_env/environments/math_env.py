"""
Math reasoning environment using GSM8K-style problems.

Loads a dataset of grade-school math word problems. Each item has:
  - prompt:  the question, wrapped in a system + user message template
  - answer:  the numeric answer string (e.g. "42")

The model is expected to produce output in the format:
  <think>
  ... chain of thought ...
  </think>
  <answer>42</answer>

Usage:
    from rl_env.environments.math_env import load_environment
    env = load_environment()
"""

import re
from datasets import load_dataset
from .base import SingleTurnEnv, Rubric
from ..rewards import exact_match, format_reward, length_penalty

SYSTEM_PROMPT = (
    "You are a math tutor. Think through the problem step by step inside "
    "<think>...</think> tags, then give your final numeric answer inside "
    "<answer>...</answer> tags."
)

_ANSWER_RE = re.compile(r"<answer>\s*([\d,\.\-]+)\s*</answer>", re.IGNORECASE)


def _extract_answer(text: str) -> str:
    """Pull the number out of <answer>N</answer>."""
    m = _ANSWER_RE.search(text)
    if m:
        return m.group(1).replace(",", "").strip()
    return text.strip()


def _normalize_gsm8k_answer(answer_str: str) -> str:
    """GSM8K stores answers as '#### 42' — extract the number."""
    parts = answer_str.split("####")
    return parts[-1].replace(",", "").strip()


def load_environment(
    split: str = "train",
    max_samples: int = 500,
    reward_config: str = "accuracy_only",  # "accuracy_only" | "accuracy_format" | "full"
) -> SingleTurnEnv:
    """
    Load a math RL environment.

    reward_config controls which reward functions are active:
      - "accuracy_only"   : only exact-match accuracy (simplest baseline)
      - "accuracy_format" : accuracy + format compliance
      - "full"            : accuracy + format + length penalty
    """
    raw = load_dataset("openai/gsm8k", "main", split=split)
    if max_samples:
        raw = raw.select(range(min(max_samples, len(raw))))

    dataset = []
    for item in raw:
        prompt = _build_prompt(item["question"])
        answer = _normalize_gsm8k_answer(item["answer"])
        dataset.append({"prompt": prompt, "answer": answer})

    rubric = _build_rubric(reward_config, extract_fn=_extract_answer)
    return SingleTurnEnv(dataset=dataset, rubric=rubric)


def _build_prompt(question: str) -> str:
    return (
        f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n{question}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def _build_rubric(config: str, extract_fn) -> Rubric:
    """
    Build a Rubric from a named config.

    This is the key function you'll modify to experiment with reward functions.
    Adding a new config here = defining a new reward experiment.
    """

    def accuracy(completion: str, answer: str) -> float:
        return exact_match.score(extract_fn(completion), answer)

    def fmt(completion: str, answer: str) -> float:
        return format_reward.score(completion)

    def length(completion: str, answer: str) -> float:
        return length_penalty.score(completion, target_tokens=150)

    configs = {
        "accuracy_only": (
            [accuracy],
            [1.0],
        ),
        "accuracy_format": (
            [accuracy, fmt],
            [0.8, 0.2],
        ),
        "full": (
            [accuracy, fmt, length],
            [0.7, 0.2, 0.1],
        ),
    }

    if config not in configs:
        raise ValueError(f"Unknown reward_config '{config}'. Choose from: {list(configs)}")

    funcs, weights = configs[config]
    return Rubric(funcs=funcs, weights=weights)

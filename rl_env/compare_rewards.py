"""
Reward function comparison tool — no GPU needed.

This lets you quickly test and compare different reward functions
on a batch of (completion, answer) pairs WITHOUT running full training.

Use this to:
  1. Sanity-check your reward functions before training
  2. Understand what signal each function provides
  3. Spot reward hacking potential (e.g. format reward gaming)

Usage:
    python -m rl_env.compare_rewards
"""

from .environments.math_env import load_environment
from .rewards import exact_match, format_reward, length_penalty

# ── Synthetic examples to test reward behavior ──────────────────────────────
EXAMPLES = [
    {
        "label": "correct + good format",
        "completion": "<think>3 * 7 = 21</think>\n<answer>21</answer>",
        "answer": "21",
    },
    {
        "label": "correct + no format",
        "completion": "The answer is 21.",
        "answer": "21",
    },
    {
        "label": "wrong + good format",
        "completion": "<think>3 * 8 = 24</think>\n<answer>24</answer>",
        "answer": "21",
    },
    {
        "label": "wrong + no format",
        "completion": "The answer is 24.",
        "answer": "21",
    },
    {
        "label": "correct + format but empty answer tag (reward hack attempt)",
        "completion": "<think>some reasoning</think>\n<answer></answer>\n21",
        "answer": "21",
    },
    {
        "label": "very long correct answer (length penalty test)",
        "completion": (
            "<think>" + "Let me think step by step. " * 80 + "</think>\n<answer>21</answer>"
        ),
        "answer": "21",
    },
    {
        "label": "very short correct answer",
        "completion": "<answer>21</answer>",
        "answer": "21",
    },
]


def print_comparison():
    print("\n" + "=" * 70)
    print("  REWARD FUNCTION COMPARISON")
    print("=" * 70)

    # Header
    col_w = 14
    print(f"\n{'Example':<35} {'accuracy':>{col_w}} {'format':>{col_w}} {'length(150)':>{col_w}}")
    print("-" * 70)

    for ex in EXAMPLES:
        acc = exact_match.score(
            _extract_answer(ex["completion"]), ex["answer"]
        )
        fmt = format_reward.score(ex["completion"])
        lng = length_penalty.score(ex["completion"], target_tokens=150)

        label = ex["label"][:34]
        print(f"{label:<35} {acc:>{col_w}.2f} {fmt:>{col_w}.2f} {lng:>{col_w}.3f}")

    print("\n" + "=" * 70)
    print("\nWeighted totals under each reward_config:\n")

    configs = {
        "accuracy_only":   {"accuracy": 1.0,  "format": 0.0,  "length": 0.0},
        "accuracy_format": {"accuracy": 0.8,  "format": 0.2,  "length": 0.0},
        "full":            {"accuracy": 0.7,  "format": 0.2,  "length": 0.1},
    }

    for config_name, weights in configs.items():
        print(f"  {config_name}:")
        for ex in EXAMPLES:
            acc = exact_match.score(_extract_answer(ex["completion"]), ex["answer"])
            fmt = format_reward.score(ex["completion"])
            lng = length_penalty.score(ex["completion"], target_tokens=150)
            total = (
                weights["accuracy"] * acc
                + weights["format"] * fmt
                + weights["length"] * lng
            )
            label = ex["label"][:45]
            print(f"    {label:<46} -> {total:.3f}")
        print()

    print("Key things to notice:")
    print("  - 'correct + no format' gets 1.0 with accuracy_only but loses points in other configs")
    print("  - 'wrong + good format' gets 0.0 with accuracy_only but gets partial reward with accuracy_format")
    print("  - 'empty answer tag hack' reveals potential reward hacking with format reward")
    print("  - These tradeoffs determine what behavior you incentivize in training\n")


import re
_ANSWER_RE = re.compile(r"<answer>\s*([\d,\.\-]+)\s*</answer>", re.IGNORECASE)

def _extract_answer(text: str) -> str:
    m = _ANSWER_RE.search(text)
    if m:
        return m.group(1).replace(",", "").strip()
    # fallback: extract any number from the text
    nums = re.findall(r"\b\d+\.?\d*\b", text)
    return nums[-1] if nums else text.strip()


if __name__ == "__main__":
    print_comparison()

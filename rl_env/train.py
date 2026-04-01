"""
GRPO training script for a single-turn RL environment.

Uses HuggingFace TRL's GRPOTrainer — the simplest way to run GRPO.
Reference: https://huggingface.co/learn/cookbook/en/fine_tuning_llm_grpo_trl

Usage:
    # Quick test run (CPU, tiny model, few steps)
    python -m rl_env.train --model Qwen/Qwen2.5-0.5B-Instruct --reward_config accuracy_only --max_steps 50

    # Experiment: compare format reward vs no format reward
    python -m rl_env.train --reward_config accuracy_format --run_name exp_with_format

How GRPO works (single-turn):
    1. For each prompt, generate G completions (group_size, default 8)
    2. Score each with the reward function -> r_i
    3. Compute group-relative advantage: A_i = (r_i - mean(r)) / std(r)
    4. Update policy to increase probability of high-advantage completions
    5. Clip updates like PPO to prevent policy collapse

Key hyperparameters to experiment with:
    --group_size     : how many completions per prompt (more = better baseline, slower)
    --reward_config  : which reward function combination to use
    --learning_rate  : too high -> instability, too low -> no learning
"""

import argparse
import os
from typing import List

from datasets import Dataset
from trl import GRPOConfig, GRPOTrainer
from transformers import AutoTokenizer

from .environments.math_env import load_environment
from .environments.base import SingleTurnEnv


def build_trl_dataset(env: SingleTurnEnv) -> Dataset:
    """
    TRL's GRPOTrainer expects a HuggingFace Dataset with a 'prompt' column.
    We also attach 'answer' so the reward function can access it.
    """
    return Dataset.from_list(env.dataset)


def make_reward_fn(env: SingleTurnEnv):
    """
    Wrap the environment's rubric into the format TRL expects.

    TRL reward fn signature: (completions: List[str], **kwargs) -> List[float]
    The 'answer' column from the dataset is passed via kwargs.
    """
    def reward_fn(completions: List[str], answer: List[str], **kwargs) -> List[float]:
        scores = env.score_batch(completions, answer)
        return [s["total"] for s in scores]

    return reward_fn


def make_per_reward_fns(env: SingleTurnEnv):
    """
    Create separate reward functions for each component so TRL logs them
    individually — this is how you see how each reward evolves during training.
    """
    per_fns = []
    for fn, w in zip(env.rubric.funcs, env.rubric.weights):
        fn_ref = fn  # capture in closure
        w_ref = w

        def make_fn(f, weight):
            import asyncio

            def component_fn(completions: List[str], answer: List[str], **kwargs) -> List[float]:
                results = []
                for comp, ans in zip(completions, answer):
                    if asyncio.iscoroutinefunction(f):
                        val = asyncio.run(f(comp, ans))
                    else:
                        val = f(comp, ans)
                    results.append(val * weight)
                return results

            component_fn.__name__ = f"reward_{f.__name__}"
            return component_fn

        per_fns.append(make_fn(fn_ref, w_ref))

    return per_fns


def parse_args():
    parser = argparse.ArgumentParser(description="GRPO training on a single-turn RL env")
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="HuggingFace model ID to train",
    )
    parser.add_argument(
        "--reward_config",
        default="accuracy_only",
        choices=["accuracy_only", "accuracy_format", "full"],
        help="Which reward function combination to use (see math_env.py)",
    )
    parser.add_argument("--max_samples", type=int, default=200)
    parser.add_argument("--max_steps", type=int, default=200)
    parser.add_argument("--group_size", type=int, default=8,
                        help="GRPO group size G: completions per prompt")
    parser.add_argument("--learning_rate", type=float, default=5e-7)
    parser.add_argument("--max_completion_length", type=int, default=512)
    parser.add_argument("--run_name", default=None,
                        help="WandB run name (also used for output dir)")
    parser.add_argument("--output_dir", default="./outputs")
    return parser.parse_args()


def main():
    args = parse_args()
    run_name = args.run_name or f"grpo_{args.reward_config}"

    print(f"\n{'='*60}")
    print(f"  GRPO Training Run: {run_name}")
    print(f"  Model:         {args.model}")
    print(f"  Reward config: {args.reward_config}")
    print(f"  Group size:    {args.group_size}")
    print(f"  Max steps:     {args.max_steps}")
    print(f"{'='*60}\n")

    # 1. Load environment
    env = load_environment(
        split="train",
        max_samples=args.max_samples,
        reward_config=args.reward_config,
    )
    print(f"Loaded {len(env)} training examples")

    # 2. Build dataset for TRL
    dataset = build_trl_dataset(env)

    # 3. Build reward function(s) — one per rubric component for detailed logging
    reward_fns = make_per_reward_fns(env)

    # 4. Configure GRPO
    training_args = GRPOConfig(
        output_dir=os.path.join(args.output_dir, run_name),
        run_name=run_name,
        learning_rate=args.learning_rate,
        num_train_epochs=1,
        max_steps=args.max_steps,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_generations=args.group_size,       # GRPO group size G
        max_completion_length=args.max_completion_length,
        # Logging
        logging_steps=10,
        report_to="none",  # change to "wandb" when you want experiment tracking
        save_steps=100,
        # GRPO-specific
        temperature=0.9,                        # generation temperature
        beta=0.001,                             # KL penalty coefficient
    )

    # 5. Train
    trainer = GRPOTrainer(
        model=args.model,
        args=training_args,
        train_dataset=dataset,
        reward_funcs=reward_fns,
    )

    print("Starting training...\n")
    trainer.train()

    print(f"\nDone. Model saved to {training_args.output_dir}")


if __name__ == "__main__":
    main()

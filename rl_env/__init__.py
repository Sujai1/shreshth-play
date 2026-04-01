"""
RL environment sandbox for LLM training experiments.

Structure mirrors Prime Intellect's verifiers library:
  https://github.com/PrimeIntellect-ai/verifiers

Quickstart:
    from rl_env.environments.math_env import load_environment
    env = load_environment(reward_config="accuracy_format")

    scores = env.score_batch(
        completions=["<think>2+2=4</think><answer>4</answer>"],
        answers=["4"],
    )
"""

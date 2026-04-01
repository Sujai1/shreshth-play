"""
Tests for reward functions.

These test the reward functions directly — no model or GPU needed.
Run with: python -m pytest tests/test_rewards.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rl_env.rewards import exact_match, format_reward, length_penalty


# ── exact_match tests ────────────────────────────────────────────────────────

class TestExactMatch:
    def test_exact_match_correct(self):
        assert exact_match.score("42", "42") == 1.0

    def test_exact_match_wrong(self):
        assert exact_match.score("41", "42") == 0.0

    def test_exact_match_whitespace_stripped(self):
        assert exact_match.score("  42  ", "42") == 1.0

    def test_exact_match_case_sensitive(self):
        # Numeric answers are strings — "42" != "42.0"
        assert exact_match.score("42.0", "42") == 0.0

    def test_soft_score_close(self):
        assert exact_match.soft_score("42.001", "42", tolerance=0.01) == 1.0

    def test_soft_score_too_far(self):
        assert exact_match.soft_score("50", "42", tolerance=0.01) == 0.0

    def test_soft_score_zero_gt(self):
        assert exact_match.soft_score("0", "0") == 1.0
        assert exact_match.soft_score("1", "0") == 0.0

    def test_soft_score_non_numeric_returns_zero(self):
        assert exact_match.soft_score("forty-two", "42") == 0.0


# ── format_reward tests ──────────────────────────────────────────────────────

class TestFormatReward:
    def test_perfect_format(self):
        text = "<think>3*7=21</think>\n<answer>21</answer>"
        assert format_reward.score(text) == 1.0

    def test_only_think_tag(self):
        text = "<think>reasoning here</think>"
        score = format_reward.score(text)
        assert score == pytest.approx(0.5)

    def test_only_answer_tag(self):
        text = "<answer>42</answer>"
        score = format_reward.score(text)
        assert score == pytest.approx(0.5)

    def test_no_tags(self):
        text = "The answer is 42."
        assert format_reward.score(text) == 0.0

    def test_empty_answer_tag_penalized(self):
        text = "<think>reasoning</think>\n<answer></answer>"
        score = format_reward.score(text)
        # Should be < 1.0 due to penalty for empty answer tag
        assert score < 1.0

    def test_answer_with_digits_no_penalty(self):
        text = "<think>reasoning</think>\n<answer>42</answer>"
        assert format_reward.score(text) == 1.0

    def test_strict_score_correct_order(self):
        text = "<think>reasoning</think>\n<answer>42</answer>"
        assert format_reward.strict_score(text) == 1.0

    def test_strict_score_wrong_order(self):
        text = "<answer>42</answer>\n<think>reasoning</think>"
        assert format_reward.strict_score(text) == 0.0

    def test_strict_score_missing_tags(self):
        text = "The answer is 42."
        assert format_reward.strict_score(text) == 0.0


# ── length_penalty tests ─────────────────────────────────────────────────────

class TestLengthPenalty:
    def test_exact_target_returns_one(self):
        # ~150 tokens -> ~115 words (150 / 1.3)
        words_at_target = int(150 / 1.3)
        text = " ".join(["word"] * words_at_target)
        score = length_penalty.score(text, target_tokens=150)
        assert score == pytest.approx(1.0, abs=0.05)

    def test_too_short_penalized(self):
        text = "short"
        score = length_penalty.score(text, target_tokens=150)
        assert score < 0.5  # far from target -> low score

    def test_too_long_penalized(self):
        text = " ".join(["word"] * 1000)
        score = length_penalty.score(text, target_tokens=150)
        assert score < 0.1

    def test_score_in_range(self):
        for n_words in [5, 50, 115, 300, 800]:
            text = " ".join(["word"] * n_words)
            score = length_penalty.score(text, target_tokens=150)
            assert 0.0 <= score <= 1.0

    def test_hard_penalty_in_range(self):
        text = " ".join(["word"] * 100)  # ~130 tokens
        assert length_penalty.hard_penalty(text, min_tokens=20, max_tokens=500) == 1.0

    def test_hard_penalty_too_short(self):
        text = "hi"
        assert length_penalty.hard_penalty(text, min_tokens=20, max_tokens=500) == 0.0

    def test_hard_penalty_too_long(self):
        text = " ".join(["word"] * 1000)
        assert length_penalty.hard_penalty(text, min_tokens=20, max_tokens=500) == 0.0


# ── Rubric integration tests ─────────────────────────────────────────────────

class TestRubric:
    def test_rubric_single_fn(self):
        from rl_env.environments.base import Rubric

        def accuracy(completion, answer):
            return exact_match.score(completion, answer)

        rubric = Rubric(funcs=[accuracy], weights=[1.0])
        scores = rubric.score("42", "42")
        assert scores["accuracy"] == 1.0
        assert scores["total"] == 1.0

    def test_rubric_weighted_combination(self):
        from rl_env.environments.base import Rubric

        def accuracy(completion, answer):
            return 1.0  # always correct

        def fmt(completion, answer):
            return 0.5  # half format score

        rubric = Rubric(funcs=[accuracy, fmt], weights=[0.8, 0.2])
        scores = rubric.score("any", "any")
        assert scores["total"] == pytest.approx(0.8 * 1.0 + 0.2 * 0.5)

    def test_rubric_weights_must_sum_to_one(self):
        from rl_env.environments.base import Rubric

        def fn(c, a):
            return 1.0

        with pytest.raises(AssertionError):
            Rubric(funcs=[fn], weights=[0.5])  # doesn't sum to 1

    def test_rubric_score_returns_per_fn_names(self):
        from rl_env.environments.base import Rubric

        def my_reward(completion, answer):
            return 0.7

        rubric = Rubric(funcs=[my_reward], weights=[1.0])
        scores = rubric.score("x", "x")
        assert "my_reward" in scores
        assert "total" in scores

"""
Tests for the SingleTurnEnv class and math environment loader.

These test environment wiring — no model or network needed
(we mock the dataset loader to avoid downloading GSM8K).

Run with: python -m pytest tests/test_environment.py -v
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rl_env.environments.base import SingleTurnEnv, Rubric


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_dummy_env(reward_fn=None):
    """Create a SingleTurnEnv with synthetic data for testing."""
    dataset = [
        {"prompt": "What is 2+2?", "answer": "4"},
        {"prompt": "What is 3*3?", "answer": "9"},
        {"prompt": "What is 10-5?", "answer": "5"},
    ]

    def default_reward(completion, answer):
        return 1.0 if completion.strip() == answer.strip() else 0.0

    fn = reward_fn or default_reward
    rubric = Rubric(funcs=[fn], weights=[1.0])
    return SingleTurnEnv(dataset=dataset, rubric=rubric)


# ── SingleTurnEnv tests ──────────────────────────────────────────────────────

class TestSingleTurnEnv:
    def test_len(self):
        env = make_dummy_env()
        assert len(env) == 3

    def test_get_batch_returns_correct_items(self):
        env = make_dummy_env()
        batch = env.get_batch([0, 2])
        assert len(batch) == 2
        assert batch[0]["answer"] == "4"
        assert batch[1]["answer"] == "5"

    def test_score_completion_correct(self):
        env = make_dummy_env()
        scores = env.score_completion(completion="4", answer="4")
        assert scores["total"] == 1.0

    def test_score_completion_wrong(self):
        env = make_dummy_env()
        scores = env.score_completion(completion="99", answer="4")
        assert scores["total"] == 0.0

    def test_score_batch_returns_list(self):
        env = make_dummy_env()
        results = env.score_batch(
            completions=["4", "9", "wrong"],
            answers=["4", "9", "5"],
        )
        assert len(results) == 3
        assert results[0]["total"] == 1.0
        assert results[1]["total"] == 1.0
        assert results[2]["total"] == 0.0

    def test_score_batch_mismatched_lengths_raises(self):
        env = make_dummy_env()
        with pytest.raises((ValueError, Exception)):
            env.score_batch(completions=["4"], answers=["4", "9"])

    def test_rubric_scores_labeled_by_fn_name(self):
        env = make_dummy_env()
        scores = env.score_completion("4", "4")
        # The reward function is named "default_reward"
        assert "default_reward" in scores

    def test_rubric_weights_normalization(self):
        """Rubric with wrong weights should raise on construction."""

        def fn(c, a):
            return 1.0

        with pytest.raises(AssertionError):
            Rubric(funcs=[fn], weights=[0.7])  # must sum to 1.0

    def test_composite_rubric_weighted_total(self):
        """Test that weighted totals are computed correctly."""

        def always_one(completion, answer):
            return 1.0

        def always_half(completion, answer):
            return 0.5

        rubric = Rubric(funcs=[always_one, always_half], weights=[0.6, 0.4])
        env = SingleTurnEnv(
            dataset=[{"prompt": "q", "answer": "a"}],
            rubric=rubric,
        )
        scores = env.score_completion("x", "y")
        expected = 0.6 * 1.0 + 0.4 * 0.5
        assert scores["total"] == pytest.approx(expected)


# ── load_environment tests (mocked) ─────────────────────────────────────────

class TestLoadEnvironment:
    def _make_mock_dataset(self, n=5):
        items = [
            {"question": f"What is {i}+{i}?", "answer": f"Some reasoning #### {i*2}"}
            for i in range(1, n + 1)
        ]
        mock_ds = MagicMock()
        mock_ds.__iter__ = lambda self: iter(items)
        mock_ds.__len__ = lambda self: n
        mock_ds.select = lambda indices: mock_ds
        return mock_ds

    @patch("rl_env.environments.math_env.load_dataset")
    def test_loads_with_accuracy_only(self, mock_load):
        mock_load.return_value = self._make_mock_dataset()
        from rl_env.environments.math_env import load_environment
        env = load_environment(reward_config="accuracy_only")
        assert len(env) > 0

    @patch("rl_env.environments.math_env.load_dataset")
    def test_loads_with_accuracy_format(self, mock_load):
        mock_load.return_value = self._make_mock_dataset()
        from rl_env.environments.math_env import load_environment
        env = load_environment(reward_config="accuracy_format")
        assert env.rubric.weights == [0.8, 0.2]

    @patch("rl_env.environments.math_env.load_dataset")
    def test_loads_with_full_config(self, mock_load):
        mock_load.return_value = self._make_mock_dataset()
        from rl_env.environments.math_env import load_environment
        env = load_environment(reward_config="full")
        assert len(env.rubric.funcs) == 3

    @patch("rl_env.environments.math_env.load_dataset")
    def test_invalid_reward_config_raises(self, mock_load):
        mock_load.return_value = self._make_mock_dataset()
        from rl_env.environments.math_env import load_environment
        with pytest.raises(ValueError, match="Unknown reward_config"):
            load_environment(reward_config="nonexistent_config")

    @patch("rl_env.environments.math_env.load_dataset")
    def test_gsm8k_answer_normalization(self, mock_load):
        """GSM8K answers have '#### N' format — verify we strip it correctly."""
        items = [{"question": "Q", "answer": "Some work\n#### 42"}]
        mock_ds = MagicMock()
        mock_ds.__iter__ = lambda self: iter(items)
        mock_ds.__len__ = lambda self: 1
        mock_ds.select = lambda indices: mock_ds
        mock_load.return_value = mock_ds

        from rl_env.environments.math_env import load_environment
        env = load_environment(reward_config="accuracy_only")

        # The stored answer should be "42" not "#### 42"
        assert env.dataset[0]["answer"] == "42"

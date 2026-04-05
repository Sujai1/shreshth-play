from src.utils import compute_statistics, validate_data, format_metrics
import pytest


def test_compute_statistics_basic():
    data = [1, 2, 3, 4, 5]
    stats = compute_statistics(data)
    assert stats["count"] == 5
    assert stats["mean"] == 3.0
    assert stats["median"] == 3
    assert stats["min"] == 1
    assert stats["max"] == 5


def test_compute_statistics_single():
    stats = compute_statistics([42])
    assert stats["count"] == 1
    assert stats["mean"] == 42
    assert stats["median"] == 42


def test_validate_data_empty():
    with pytest.raises(ValueError):
        validate_data([])


def test_validate_data_wrong_type():
    with pytest.raises(TypeError):
        validate_data("not a list")


def test_validate_data_bad_items():
    with pytest.raises(TypeError):
        validate_data([1, 2, "three"])


def test_format_metrics():
    metrics = {"loss": 0.1234, "accuracy": 0.9876, "epoch": 5}
    result = format_metrics(metrics)
    assert "loss: 0.1234" in result
    assert "accuracy: 0.9876" in result
    assert "epoch: 5" in result

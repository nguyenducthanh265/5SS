import pytest

pytest.importorskip("sklearn")  # phần train: requirements.txt
from mlkit import metrics  # noqa: E402


def test_summarize_perfect_and_wrong():
    m = metrics.summarize([0, 1, 1], [0, 1, 1], ["a", "b"])
    assert m["accuracy"] == 1.0 and m["macro_f1"] == 1.0
    m = metrics.summarize([0, 0, 1], [1, 1, 0], ["a", "b"])
    assert m["accuracy"] == 0.0 and m["confusion"] == [[0, 2], [1, 0]]


def test_baseline_predicts_majority_of_train():
    b = metrics.majority_baseline([0, 0, 0, 1], [0, 1, 1, 1], ["a", "b"])
    assert b["accuracy"] == 0.25  # luôn đoán lớp 0


def test_missing_class_in_predictions_does_not_crash():
    m = metrics.summarize([0, 1, 2], [0, 0, 0], ["a", "b", "c"])
    assert m["per_class"]["c"]["f1"] == 0.0


def test_bootstrap_ci_brackets_accuracy():
    y = [0, 1] * 50
    p = [0, 1] * 45 + [1, 0] * 5
    lo, hi = metrics.bootstrap_ci(y, p, n=500)
    assert lo <= 0.9 <= hi and hi - lo < 0.2

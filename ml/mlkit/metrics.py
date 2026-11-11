"""Số liệu đánh giá (numpy + sklearn, không cần torch)."""
from __future__ import annotations

from collections import Counter

import numpy as np
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support, roc_auc_score)


def summarize(y_true, y_pred, classes, proba=None):
    """Số liệu phân loại. Truyền proba (n, số_lớp) để có thêm AUROC (nhị phân hoặc đa lớp)."""
    labels = list(range(len(classes)))
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    out = {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "per_class": {
            c: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(s[i])}
            for i, c in enumerate(classes)
        },
        "confusion": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }
    if proba is not None and len(set(y_true)) > 1:
        proba = np.asarray(proba)
        try:
            out["auroc"] = float(roc_auc_score(y_true, proba[:, 1] if len(classes) == 2 else proba, multi_class="ovr", labels=labels))
        except ValueError:
            pass  # thiếu lớp trong tập đánh giá
    return out


def regression_summary(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    err = y_pred - y_true
    ss_tot = float(((y_true - y_true.mean()) ** 2).sum())
    return {
        "n": int(len(y_true)),
        "rmse": float(np.sqrt((err ** 2).mean())),
        "mae": float(np.abs(err).mean()),
        "r2": float(1 - (err ** 2).sum() / ss_tot) if ss_tot > 0 else 0.0,
    }


def mean_baseline(y_train, y_eval):
    """Baseline hồi quy: luôn đoán trung bình của tập train."""
    return regression_summary(y_eval, [float(np.mean(y_train))] * len(y_eval))


def majority_baseline(y_train, y_eval, classes):
    """Baseline ngu ngốc nhất: luôn đoán lớp phổ biến nhất của tập train. Mô hình phải thắng được cái này."""
    guess = Counter(y_train).most_common(1)[0][0]
    return summarize(y_eval, [guess] * len(y_eval), classes)


def bootstrap_ci(y_true, y_pred, n=1000, seed=0, alpha=0.05):
    """Khoảng tin cậy 95% của accuracy, để biết chênh lệch giữa hai mô hình có thật hay chỉ là nhiễu."""
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    rng = np.random.default_rng(seed)
    accs = [np.mean(y_true[i] == y_pred[i]) for i in (rng.integers(0, len(y_true), len(y_true)) for _ in range(n))]
    return float(np.quantile(accs, alpha / 2)), float(np.quantile(accs, 1 - alpha / 2))

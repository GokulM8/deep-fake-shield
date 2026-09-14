"""Classification metrics without fabricated fallback values."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score, average_precision_score, precision_recall_fscore_support, roc_auc_score


def binary_metrics(labels: list[int], probabilities: list[float], threshold: float = 0.5) -> dict[str, Any]:
    y_true = np.asarray(labels, dtype=int)
    y_score = np.asarray(probabilities, dtype=float)
    y_pred = (y_score >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    negatives = max(int((y_true == 0).sum()), 1)
    positives = max(int((y_true == 1).sum()), 1)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc_score(y_true, y_score)) if len(np.unique(y_true)) == 2 else None,
        "pr_auc": float(average_precision_score(y_true, y_score)) if len(np.unique(y_true)) == 2 else None,
        "false_positive_rate": float(((y_pred == 1) & (y_true == 0)).sum() / negatives),
        "false_negative_rate": float(((y_pred == 0) & (y_true == 1)).sum() / positives),
        "support": int(len(y_true)),
    }

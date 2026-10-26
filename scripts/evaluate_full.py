"""Traceable video-level evaluation on the val and test splits through the served preprocessing.

Each video is scored by ``VideoDetector.score_frames`` (the backend's own frame sampling, Haar face
crop, transform and model), averaged over the frames that contain a face. Videos with no detectable
face are excluded from metrics and counted. The decision threshold is tuned on validation only
(Youden's J) and reported on test alongside the fixed 0.5 threshold.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.video_detector import VideoDetector, VideoInferenceError  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

SPLITS = ("val", "test")
CACHE_FIELDS = ["video_path", "label", "fake_prob", "n_valid_frames", "error"]
DEFAULT_THRESHOLD = 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--frames", type=int, required=True, help="Evenly sampled frames per video")
    parser.add_argument("--splits-dir", type=Path, default=ROOT / "artifacts/splits")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--device", default="auto", help="auto (cuda > mps > cpu), cpu, cuda, or mps")
    parser.add_argument("--limit", type=int, default=0, help="Class-stratified subset per split, for quick checks")
    parser.add_argument(
        "--video-root",
        type=Path,
        default=ROOT / "datasets/raw",
        help="Local dataset root; split paths are remapped below their datasets/raw marker",
    )
    return parser.parse_args()


def resolve_device(name: str) -> torch.device:
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def local_path(recorded: str, video_root: Path) -> Path:
    """Map a split path recorded on another machine onto the local dataset root."""
    parts = Path(recorded).parts
    for index in range(len(parts) - 1):
        if parts[index : index + 2] == ("datasets", "raw"):
            return video_root.joinpath(*parts[index + 2 :])
    return Path(recorded)


def stratified_subset(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    if not limit or limit >= len(rows):
        return rows
    by_label: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_label.setdefault(row["label"], []).append(row)
    subset = []
    for group in by_label.values():
        subset.extend(group[: max(1, round(limit * len(group) / len(rows)))])
    return subset


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_state() -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()

    try:
        # Evaluation outputs are not code, so rewriting them does not make the run dirty.
        changed = git("status", "--porcelain", "--untracked-files=no", "--", ".", ":(exclude)artifacts/evaluations")
        return {"commit": git("rev-parse", "HEAD"), "dirty": bool(changed)}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def load_cache(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["video_path"]: row for row in csv.DictReader(handle)}


def score_split(
    detector: VideoDetector, split: str, rows: list[dict[str, str]], args: argparse.Namespace
) -> list[dict[str, str]]:
    """Score every row, reusing and appending to the per-split cache so reruns are instant."""
    cache_path = args.out_dir / f"predictions_{split}.csv"
    cache = load_cache(cache_path)
    missing = [row for row in rows if row["video_path"] not in cache]
    print(f"[{split}] {len(rows)} videos, {len(rows) - len(missing)} cached, {len(missing)} to score", flush=True)

    new_file = not cache_path.is_file()
    with cache_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CACHE_FIELDS)
        if new_file:
            writer.writeheader()
        started = time.monotonic()
        for done, row in enumerate(missing, start=1):
            entry = {"video_path": row["video_path"], "label": row["label"], "fake_prob": "", "n_valid_frames": "0", "error": ""}
            try:
                scores = detector.score_frames(local_path(row["video_path"], args.video_root))
                entry["n_valid_frames"] = str(len(scores))
                if scores:
                    entry["fake_prob"] = f"{float(np.mean(scores)):.6f}"
            except VideoInferenceError as error:
                entry["error"] = str(error)
            writer.writerow(entry)
            handle.flush()
            cache[row["video_path"]] = entry
            if done % 50 == 0 or done == len(missing):
                elapsed = time.monotonic() - started
                eta = elapsed / done * (len(missing) - done)
                print(f"[{split}] {done}/{len(missing)}  {elapsed / 60:.1f} min elapsed, ~{eta / 60:.1f} min left", flush=True)
    return [cache[row["video_path"]] for row in rows]


def threshold_metrics(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    predictions = (scores >= threshold).astype(int)
    tn, fp, fn, tp = (int(value) for value in confusion_matrix(labels, predictions, labels=[0, 1]).ravel())

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    precision, recall = ratio(tp, tp + fp), ratio(tp, tp + fn)
    specificity = ratio(tn, tn + fp)
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else 0.0
    return {
        "threshold": threshold,
        "accuracy": ratio(tp + tn, len(labels)),
        "balanced_accuracy": (recall + specificity) / 2 if recall is not None and specificity is not None else None,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": specificity,
        "real_recall": specificity,
        "fake_recall": recall,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def youden_threshold(labels: np.ndarray, scores: np.ndarray) -> tuple[float, float]:
    """Threshold maximizing TPR - FPR under the ``score >= threshold`` rule; ties keep the highest."""
    fpr, tpr, thresholds = roc_curve(labels, scores)
    finite = np.isfinite(thresholds)
    j = np.where(finite, tpr - fpr, -np.inf)
    best = int(np.argmax(j))
    return float(thresholds[best]), float(j[best])


def split_summary(split: str, csv_path: Path, rows: list[dict[str, str]], scored: list[dict[str, str]]) -> dict[str, Any]:
    def counts(items: list[dict[str, str]]) -> dict[str, int]:
        return {"real": sum(item["label"] == "0" for item in items), "fake": sum(item["label"] == "1" for item in items)}

    evaluated = [item for item in scored if item["fake_prob"]]
    no_face = [item for item in scored if not item["fake_prob"] and not item["error"]]
    errors = [item for item in scored if item["error"]]
    frames = [int(item["n_valid_frames"]) for item in evaluated]
    return {
        "csv": str(csv_path.relative_to(ROOT) if csv_path.is_relative_to(ROOT) else csv_path),
        "total": len(rows),
        "class_counts": counts(rows),
        "evaluated": len(evaluated),
        "evaluated_class_counts": counts(evaluated),
        "skipped_no_face": len(no_face),
        "skipped_no_face_class_counts": counts(no_face),
        "skipped_errors": len(errors),
        "mean_valid_frames": float(np.mean(frames)) if frames else None,
        "videos_with_partial_faces": sum(count < frames_max for count in frames) if (frames_max := max(frames, default=0)) else 0,
    }


def evaluate_scores(labels: np.ndarray, scores: np.ndarray, thresholds: dict[str, float]) -> dict[str, Any]:
    both_classes = len(np.unique(labels)) == 2
    return {
        "roc_auc": float(roc_auc_score(labels, scores)) if both_classes else None,
        "pr_auc": float(average_precision_score(labels, scores)) if both_classes else None,
        "at_threshold": {name: threshold_metrics(labels, scores, value) for name, value in thresholds.items()},
    }


def plot_curves(out_dir: Path, curves: dict[str, tuple[np.ndarray, np.ndarray]], test_metrics: dict[str, Any]) -> None:
    labels, scores = curves["test"]
    markers = {"0.5": ("o", "tab:red"), "tuned": ("s", "tab:green")}

    fig, ax = plt.subplots(figsize=(5.5, 5))
    for split, (split_labels, split_scores) in curves.items():
        fpr, tpr, _ = roc_curve(split_labels, split_scores)
        ax.plot(fpr, tpr, label=f"{split} (AUC {roc_auc_score(split_labels, split_scores):.3f})", alpha=1 if split == "test" else 0.5)
    for name, metrics in test_metrics["at_threshold"].items():
        marker, color = markers[name]
        ax.scatter(1 - metrics["specificity"], metrics["recall"], marker=marker, color=color, zorder=3,
                   label=f"test @ {name} ({metrics['threshold']:.3f})")
    ax.plot([0, 1], [0, 1], "--", color="grey", linewidth=0.8)
    ax.set(xlabel="False positive rate (real flagged fake)", ylabel="True positive rate (fake recall)", title="ROC curve")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "roc_curve.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5))
    for split, (split_labels, split_scores) in curves.items():
        precision, recall, _ = precision_recall_curve(split_labels, split_scores)
        ax.plot(recall, precision, label=f"{split} (AP {average_precision_score(split_labels, split_scores):.3f})",
                alpha=1 if split == "test" else 0.5)
    for name, metrics in test_metrics["at_threshold"].items():
        marker, color = markers[name]
        ax.scatter(metrics["recall"], metrics["precision"], marker=marker, color=color, zorder=3,
                   label=f"test @ {name} ({metrics['threshold']:.3f})")
    ax.axhline(labels.mean(), linestyle="--", color="grey", linewidth=0.8, label=f"fake prevalence ({labels.mean():.3f})")
    ax.set(xlabel="Recall (fake)", ylabel="Precision (fake)", title="Precision-recall curve", ylim=(0, 1.02))
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "pr_curve.png", dpi=150)
    plt.close(fig)

    for name, metrics in test_metrics["at_threshold"].items():
        cm = metrics["confusion_matrix"]
        grid = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
        fig, ax = plt.subplots(figsize=(4.2, 3.8))
        ax.imshow(grid / grid.sum(axis=1, keepdims=True).clip(min=1), cmap="Blues", vmin=0, vmax=1)
        for (row, col), value in np.ndenumerate(grid):
            share = value / max(grid[row].sum(), 1)
            ax.text(col, row, f"{value}\n({share:.1%})", ha="center", va="center",
                    color="white" if share > 0.6 else "black", fontsize=10)
        ax.set_xticks([0, 1], ["REAL", "FAKE"])
        ax.set_yticks([0, 1], ["REAL", "FAKE"])
        ax.set(xlabel="Predicted", ylabel="Actual", title=f"Test confusion @ {metrics['threshold']:.3f}")
        fig.tight_layout()
        fig.savefig(out_dir / f"confusion_matrix_{name}.png", dpi=150)
        plt.close(fig)


def print_summary(metrics: dict[str, Any]) -> None:
    def pct(value: float | None) -> str:
        return "   —  " if value is None or (isinstance(value, float) and math.isnan(value)) else f"{value * 100:6.2f}"

    test = metrics["test"]
    print()
    print(f"Run {metrics['run_name']}: {metrics['frames']} frames, device {metrics['device']}")
    for split in SPLITS:
        info = metrics["splits"][split]
        print(f"  {split:<4} total {info['total']:>4}  evaluated {info['evaluated']:>4}  "
              f"no-face {info['skipped_no_face']:>3}  errors {info['skipped_errors']:>3}  "
              f"ROC-AUC {pct(metrics[split]['roc_auc'])}  PR-AUC {pct(metrics[split]['pr_auc'])}")
    print(f"  tuned threshold (val Youden J) = {metrics['threshold_selection']['value']:.4f}")
    header = f"  {'test @':<14}{'acc':>7}{'bal':>7}{'prec':>7}{'rec':>7}{'F1':>7}{'realR':>7}{'fakeR':>7}   TN   FP   FN   TP"
    print(header)
    for name, item in test["at_threshold"].items():
        cm = item["confusion_matrix"]
        label = f"{name} ({item['threshold']:.3f})"
        print(f"  {label:<14}{pct(item['accuracy'])} {pct(item['balanced_accuracy'])} {pct(item['precision'])} "
              f"{pct(item['recall'])} {pct(item['f1'])} {pct(item['real_recall'])} {pct(item['fake_recall'])} "
              f"{cm['tn']:>4} {cm['fp']:>4} {cm['fn']:>4} {cm['tp']:>4}")


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = args.checkpoint.resolve()
    device = resolve_device(args.device)
    run_config = {
        "checkpoint": str(checkpoint.relative_to(ROOT) if checkpoint.is_relative_to(ROOT) else checkpoint),
        "checkpoint_sha256": file_sha256(checkpoint),
        "frames": args.frames,
    }
    # Cached probabilities are only valid for the checkpoint and frame count that produced them.
    config_path = args.out_dir / "run_config.json"
    if config_path.is_file() and json.loads(config_path.read_text()) != run_config:
        print(f"Cache in {args.out_dir} was made with a different checkpoint or frame count; use another --out-dir.",
              file=sys.stderr)
        return 2
    config_path.write_text(json.dumps(run_config, indent=2) + "\n", encoding="utf-8")

    detector = VideoDetector(model_path=checkpoint, frames=args.frames, device=device)
    if detector.load_error is not None:
        print(f"Model loading failed: {detector.load_error}", file=sys.stderr)
        return 1

    summaries, arrays = {}, {}
    for split in SPLITS:
        csv_path = args.splits_dir / f"{split}.csv"
        with csv_path.open(newline="", encoding="utf-8") as handle:
            rows = stratified_subset(list(csv.DictReader(handle)), args.limit)
        scored = score_split(detector, split, rows, args)
        summaries[split] = split_summary(split, csv_path, rows, scored)
        evaluated = [item for item in scored if item["fake_prob"]]
        arrays[split] = (
            np.array([int(item["label"]) for item in evaluated]),
            np.array([float(item["fake_prob"]) for item in evaluated]),
        )

    tuned, best_j = youden_threshold(*arrays["val"])
    thresholds = {"0.5": DEFAULT_THRESHOLD, "tuned": tuned}
    results = {split: evaluate_scores(*arrays[split], thresholds) for split in SPLITS}

    metrics = {
        "run_name": args.out_dir.name,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git": git_state(),
        **run_config,
        "model": "efficientnet_b0",
        "aggregation": "mean fake probability over frames with a detected face",
        "preprocessing": "backend VideoDetector: linspace frame sampling, Haar face crop (20% margin), 224x224, ImageNet norm",
        "device": str(device),
        "limit": args.limit or None,
        "thresholds": thresholds,
        "threshold_selection": {"method": "youden_j", "split": "val", "value": tuned, "val_youden_j": best_j},
        "splits": summaries,
        "skipped_videos": sum(info["skipped_no_face"] + info["skipped_errors"] for info in summaries.values()),
        "val": results["val"],
        "test": results["test"],
    }
    (args.out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    plot_curves(args.out_dir, arrays, results["test"])
    print_summary(metrics)
    print(f"\nWrote {args.out_dir / 'metrics.json'} and plots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

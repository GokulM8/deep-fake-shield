"""Run the served detectors (DEEPFAKE_MODEL modes) on test videos and check them against Colab.

By default scores 20 stratified test videos per mode and prints them. With ``--colab-scores`` (a CSV
of ``video_path,fake_prob``; paths in any form that ends in ``datasets/raw/...``) it reports the
largest served-vs-Colab difference. With ``--limit 0`` it scores the whole split and also prints
ROC-AUC and balanced accuracy at each mode's serving threshold, to compare with the Colab table.

    backend/.venv/bin/python scripts/check_head_parity.py --models mlp temporal --device mps
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_full import local_path, resolve_device, stratified_subset  # noqa: E402
from extract_embeddings import relative_video_path  # noqa: E402

from app.services.video_detector import create_detector  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=["mlp", "temporal"], choices=["mlp", "temporal", "baseline"])
    parser.add_argument("--split", default="test")
    parser.add_argument("--limit", type=int, default=20, help="Stratified video count; 0 = whole split")
    parser.add_argument("--device", default="cpu", help="cpu, mps, cuda or auto")
    parser.add_argument("--video-root", type=Path, default=ROOT / "datasets/raw")
    parser.add_argument("--colab-scores", type=Path, help="CSV with video_path,fake_prob from the Colab run")
    parser.add_argument("--tolerance", type=float, default=1e-3)
    parser.add_argument("--out", type=Path, help="Write per-video served scores to this CSV")
    args = parser.parse_args()

    with (ROOT / "artifacts/splits" / f"{args.split}.csv").open(newline="", encoding="utf-8") as handle:
        rows = stratified_subset(list(csv.DictReader(handle)), args.limit)
    colab: dict[str, float] = {}
    if args.colab_scores:
        with args.colab_scores.open(newline="", encoding="utf-8") as handle:
            colab = {relative_video_path(row["video_path"]): float(row["fake_prob"]) for row in csv.DictReader(handle)}

    device = resolve_device(args.device)
    labels = np.array([int(row["label"]) for row in rows])
    results: dict[str, list[float | None]] = {}
    failed = False
    for mode in args.models:
        detector = create_detector(mode, device=device)
        if detector.load_error is not None:
            print(f"{mode}: cannot load ({detector.load_error})", file=sys.stderr)
            return 1
        started = time.perf_counter()
        scores = [detector.score_video(local_path(row["video_path"], args.video_root)) for row in rows]
        elapsed = time.perf_counter() - started
        results[mode] = scores
        print(f"\n{mode} ({detector.inference_mode}, threshold {detector.threshold:.4f}, {device}): "
              f"{len(rows)} videos in {elapsed:.1f} s ({elapsed / len(rows):.2f} s/video)")
        if args.limit and len(rows) <= 40:
            for row, score in zip(rows, scores):
                shown = "no face" if score is None else f"{score:.6f}"
                print(f"  label {row['label']}  {shown:>10}  {relative_video_path(row['video_path'])}")

        valid = np.array([score is not None for score in scores])
        values = np.array([score for score in scores if score is not None])
        print(f"  no-face videos: {int((~valid).sum())}")
        if len(set(labels[valid])) == 2:
            predicted = values >= detector.threshold
            truth = labels[valid] == 1
            balanced = (predicted[truth].mean() + (~predicted[~truth]).mean()) / 2
            print(f"  ROC-AUC {roc_auc_score(truth, values):.4f}, balanced acc @ {detector.threshold:.4f}: {balanced:.4f}"
                  + ("  (subset only, not comparable to the full-split table)" if args.limit else ""))
        if colab:
            pairs = [(colab[key], score) for row, score in zip(rows, scores)
                     if score is not None and (key := relative_video_path(row["video_path"])) in colab]
            if pairs:
                worst = max(abs(a - b) for a, b in pairs)
                verdict = "PASS" if worst <= args.tolerance else "FAIL"
                failed |= verdict == "FAIL"
                print(f"  vs Colab: {len(pairs)} matched, max |diff| {worst:.2e} -> {verdict} (tolerance {args.tolerance:g})")
            else:
                print("  vs Colab: no matching videos in the scores file")

    if args.out:
        with args.out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["video_path", "label", *results])
            for index, row in enumerate(rows):
                writer.writerow([relative_video_path(row["video_path"]), row["label"],
                                 *("" if results[mode][index] is None else f"{results[mode][index]:.6f}" for mode in results)])
        print(f"\nWrote {args.out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

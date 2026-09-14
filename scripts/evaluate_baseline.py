"""Evaluate a frame baseline at video level on a held-out split."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
from evaluation.metrics import binary_metrics
from inference.video_inference import predict_video
from models.efficientnet_baseline import build_model


def balanced_rows(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    if not limit or limit >= len(rows):
        return rows
    by_label = {"0": [], "1": []}
    for row in rows:
        by_label[row["label"]].append(row)
    per_class = limit // 2
    return by_label["0"][:per_class] + by_label["1"][:per_class]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "artifacts/splits/test.csv")
    parser.add_argument("--video-root", type=Path, help="Mounted dataset root containing the raw dataset folders")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/evaluation")
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    rows = list(csv.DictReader(args.csv.open(encoding="utf-8")))
    rows = balanced_rows(rows, args.limit)
    if args.video_root:
        marker = Path("datasets/raw")
        for row in rows:
            original = Path(row["video_path"])
            try:
                marker_index = next(index for index in range(len(original.parts) - 1) if Path(*original.parts[index : index + 2]) == marker)
                candidate = args.video_root / Path(*original.parts[marker_index + len(marker.parts) :])
                row["video_path"] = str(candidate)
            except (ValueError, StopIteration):
                pass
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model().to(device)
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    labels, probabilities, predictions = [], [], []
    timelines = {}
    for row in rows:
        result = predict_video(model, row["video_path"], device, args.frames)
        if result["fake_probability"] is None:
            continue
        labels.append(int(row["label"]))
        probabilities.append(result["fake_probability"])
        predictions.append({
            "video_id": row["video_id"], "ground_truth": int(row["label"]),
            "video_fake_probability": result["fake_probability"],
            "video_prediction": int(result["fake_probability"] >= 0.5),
        })
        timelines[row["video_id"]] = result
    metrics = binary_metrics(labels, probabilities)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "test_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "video_predictions.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["video_id", "ground_truth", "video_fake_probability", "video_prediction"])
        writer.writeheader()
        writer.writerows(predictions)
    timeline_dir = ROOT / "artifacts/timelines"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    for video_id, timeline in timelines.items():
        (timeline_dir / f"{video_id.replace(':', '_')}.json").write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"device": str(device), "videos": len(predictions), "metrics": metrics}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

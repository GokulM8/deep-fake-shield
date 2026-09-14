"""Analyze one video with a trained EfficientNet baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
from inference.video_inference import predict_video
from models.efficientnet_baseline import build_model


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model().to(device)
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    result = predict_video(model, args.video, device, args.frames)
    probability = result["fake_probability"]
    verdict = "INCONCLUSIVE" if probability is None else "LIKELY_MANIPULATED" if probability >= 0.5 else "LIKELY_AUTHENTIC"
    payload = {
        "video_id": args.video.stem,
        "verdict": verdict,
        "model": {"name": "efficientnet_b0_frame_aggregation", "fake_probability": probability, "confidence": probability},
        "temporal_analysis": {"frames_analyzed": len(result["frame_scores"]), "suspicious_frames": result["suspicious_frames"]},
        "evidence": {"model_signal": {"fake_probability": probability}, "temporal_signal": {}, "forensic_signal": {}, "metadata_signal": {}, "provenance_signal": {}},
        "frame_scores": result["frame_scores"],
    }
    output = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

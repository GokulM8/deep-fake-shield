"""Audit the configured raw video dataset and write a JSON report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))

from data.dataset_discovery import build_report, discover_videos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=ROOT / "datasets" / "raw")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "dataset_report.json")
    args = parser.parse_args()
    records = discover_videos(args.dataset_root)
    report = build_report(args.dataset_root, records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "dataset_root", "total_videos", "readable_videos",
        "corrupted_or_unreadable_videos", "class_distribution", "videos_by_dataset",
        "videos_by_extension", "duration_seconds", "average_fps",
        "resolution_distribution", "source_grouping",
    )}, indent=2))
    print(f"Duplicate filenames: {len(report['duplicate_filenames'])}")
    print(f"Duplicate hashes: {len(report['duplicate_hashes'])}")
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

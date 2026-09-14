"""Create deterministic, video-level train/validation/test CSV files."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))

from data.split_dataset import create_splits, write_split_csvs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts" / "dataset_report.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "artifacts" / "splits")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    splits = create_splits(report["records"], seed=args.seed)
    write_split_csvs(splits, args.output_root)
    for name in ("train", "val", "test"):
        counts = Counter(record["label_name"] for record in splits[name])
        print(f"{name.title()}: {len(splits[name])} (Real: {counts['real']}, Fake: {counts['fake']})")
    print("Source-level split: unavailable; no source/identity metadata was found.")
    print(f"Splits: {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

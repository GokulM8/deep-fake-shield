"""Create deterministic video-level splits from an audit record list."""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def create_splits(records: list[dict[str, Any]], seed: int = 42) -> dict[str, list[dict[str, Any]]]:
    labeled = [record for record in records if record["label"] in (0, 1) and record["readable"] is True]
    hash_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in labeled:
        hash_groups[record["sha256"] or record["video_id"]].append(record)
    if any(len({record["label"] for record in group}) > 1 for group in hash_groups.values()):
        raise ValueError("Conflicting labels were found for an identical file hash; refusing to split.")

    rng = random.Random(seed)
    groups_by_label: dict[int, list[list[dict[str, Any]]]] = defaultdict(list)
    for group in hash_groups.values():
        groups_by_label[group[0]["label"]].append(group)
    result = {"train": [], "val": [], "test": []}
    for label, groups in groups_by_label.items():
        rng.shuffle(groups)
        total = sum(len(group) for group in groups)
        train_target = round(total * 0.70)
        val_target = round(total * 0.15)
        counts = {"train": 0, "val": 0, "test": 0}
        for group in groups:
            remaining = sorted(("train", "val", "test"), key=lambda name: counts[name])
            if counts["train"] < train_target and remaining[0] == "train":
                split = "train"
            elif counts["val"] < val_target and remaining[0] == "val":
                split = "val"
            elif counts["train"] < train_target:
                split = "train"
            elif counts["val"] < val_target:
                split = "val"
            else:
                split = "test"
            result[split].extend(group)
            counts[split] += len(group)
    for split in result:
        result[split].sort(key=lambda record: record["video_id"])
    _verify_no_hash_overlap(result)
    return result


def _verify_no_hash_overlap(splits: dict[str, list[dict[str, Any]]]) -> None:
    seen: dict[str, str] = {}
    for split, records in splits.items():
        for record in records:
            file_hash = record.get("sha256") or record["video_id"]
            if file_hash in seen and seen[file_hash] != split:
                raise ValueError(f"Duplicate hash crosses {seen[file_hash]} and {split}: {file_hash}")
            seen[file_hash] = split


def write_split_csvs(splits: dict[str, list[dict[str, Any]]], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    fields = ["video_path", "label", "source", "dataset", "video_id", "sha256"]
    for split, records in splits.items():
        with (output_root / f"{split}.csv").open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fields)
            writer.writeheader()
            for record in records:
                writer.writerow({field: record.get(field) if record.get(field) is not None else "" for field in fields})

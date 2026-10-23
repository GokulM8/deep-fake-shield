"""Inspect downloaded deepfake datasets without modifying their contents.

The script intentionally makes no assumptions about a particular dataset layout.
Pass the actual dataset roots with --faceforensics and --celebdf.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
MANIPULATION_NAMES = {
    "deepfake": "DeepFakes",
    "deepfakes": "DeepFakes",
    "face2face": "Face2Face",
    "faceshifter": "FaceShifter",
    "faceswap": "FaceSwap",
    "neuraltextures": "NeuralTextures",
    "fake": "Unknown manipulation",
    "manipulated": "Unknown manipulation",
}
REAL_MARKERS = {"original", "real", "youtube"}


@dataclass
class MediaRecord:
    path: str
    extension: str
    size_bytes: int
    kind: str
    label: str
    manipulation: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    duration_seconds: float | None = None
    frame_count: int | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--faceforensics", type=Path, required=True)
    parser.add_argument("--celebdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/dataset_inventory.json"))
    parser.add_argument("--max-video-probes", type=int, default=500)
    return parser.parse_args()


def iter_media(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS | IMAGE_EXTENSIONS
    )


def infer_label(path: Path, root: Path) -> tuple[str, str | None]:
    # Dataset labels are inferred from containing directories, never filenames.
    # This avoids classifying repository screenshots such as ex_deepfakes.png.
    relative_parent = path.parent.relative_to(root)
    parts = {part.lower().replace("_", "") for part in relative_parent.parts}
    for marker, manipulation in MANIPULATION_NAMES.items():
        if marker in parts or any(marker in part for part in parts):
            return "fake", manipulation
    if parts & REAL_MARKERS:
        return "real", None
    return "unknown", None


def probe_video(path: Path) -> dict[str, Any]:
    try:
        import cv2  # type: ignore
    except ImportError:
        return {}

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return {}
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0) or None
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0) or None
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) or None
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) or None
    capture.release()
    duration = frame_count / fps if frame_count and fps else None
    return {
        "width": width,
        "height": height,
        "fps": round(fps, 3) if fps else None,
        "duration_seconds": round(duration, 3) if duration else None,
        "frame_count": frame_count,
    }


def inspect_dataset(name: str, root: Path, max_video_probes: int) -> dict[str, Any]:
    paths = iter_media(root)
    records: list[MediaRecord] = []
    video_probes = 0
    for path in paths:
        label, manipulation = infer_label(path, root)
        kind = "video" if path.suffix.lower() in VIDEO_EXTENSIONS else "image"
        probe = {}
        if kind == "video" and video_probes < max_video_probes:
            probe = probe_video(path)
            video_probes += 1
        records.append(
            MediaRecord(
                path=str(path),
                extension=path.suffix.lower(),
                size_bytes=path.stat().st_size,
                kind=kind,
                label=label,
                manipulation=manipulation,
                **probe,
            )
        )

    videos = [record for record in records if record.kind == "video"]
    resolutions = Counter(
        f"{record.width}x{record.height}"
        for record in videos
        if record.width and record.height
    )
    fps_values = [record.fps for record in videos if record.fps]
    durations = [record.duration_seconds for record in videos if record.duration_seconds]
    return {
        "dataset": name,
        "root": str(root),
        "root_exists": root.exists(),
        "media_files": len(records),
        "video_files": len(videos),
        "image_files": len(records) - len(videos),
        "labels": dict(Counter(record.label for record in records)),
        "manipulation_categories": dict(
            Counter(record.manipulation for record in records if record.manipulation)
        ),
        "file_extensions": dict(Counter(record.extension for record in records)),
        "total_size_bytes": sum(record.size_bytes for record in records),
        "video_statistics": {
            "probed_videos": video_probes,
            "resolutions": dict(resolutions),
            "fps_min": min(fps_values) if fps_values else None,
            "fps_max": max(fps_values) if fps_values else None,
            "duration_min_seconds": min(durations) if durations else None,
            "duration_max_seconds": max(durations) if durations else None,
        },
        "files": [asdict(record) for record in records],
    }


def main() -> int:
    args = parse_args()
    inventory = {
        "schema_version": 1,
        "note": "Inventory only; raw datasets are never modified by this script.",
        "datasets": [
            inspect_dataset("faceforensics", args.faceforensics, args.max_video_probes),
            inspect_dataset("celebdf", args.celebdf, args.max_video_probes),
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        dataset["dataset"]: {
            "root_exists": dataset["root_exists"],
            "media_files": dataset["media_files"],
            "video_files": dataset["video_files"],
            "labels": dataset["labels"],
        }
        for dataset in inventory["datasets"]
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

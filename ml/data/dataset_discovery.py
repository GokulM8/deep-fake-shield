"""Discover and audit video files without changing the raw dataset."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
REAL_MARKERS = {"real", "original"}
FAKE_MARKERS = {"fake", "manipulated", "deepfake", "deepfakes"}


def _label_for_directory(directory_name: str) -> int | None:
    normalized = directory_name.lower().replace("_", "-")
    parts = {part for part in normalized.split("-") if part}
    if parts & FAKE_MARKERS:
        return 1
    if parts & REAL_MARKERS:
        return 0
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as media_file:
        for chunk in iter(lambda: media_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe(path: Path) -> dict[str, Any]:
    try:
        import cv2
    except ImportError as error:
        return {"readable": None, "error": f"OpenCV unavailable: {error}"}

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return {"readable": False, "error": "OpenCV could not open the video"}
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    first_frame_ok, _ = capture.read()
    capture.release()
    if not first_frame_ok:
        return {"readable": False, "error": "Video opened but yielded no decodable frames"}
    duration = frame_count / fps if fps > 0 and frame_count > 0 else None
    return {
        "readable": True,
        "error": None,
        "fps": round(fps, 3) if fps > 0 else None,
        "frame_count": frame_count or None,
        "width": width or None,
        "height": height or None,
        "duration_seconds": round(duration, 3) if duration is not None else None,
    }


def discover_videos(dataset_root: Path, hash_files: bool = True) -> list[dict[str, Any]]:
    records = []
    for path in sorted(dataset_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        relative = path.relative_to(dataset_root)
        dataset_name = relative.parts[0] if len(relative.parts) > 1 else dataset_root.name
        label = _label_for_directory(dataset_name)
        probe = _probe(path)
        record = {
            "video_path": str(path),
            "relative_path": str(relative),
            "video_id": f"{dataset_name}:{path.stem}",
            "dataset": dataset_name,
            "source": None,
            "source_available": False,
            "label": label,
            "label_name": {0: "real", 1: "fake"}.get(label, "unknown"),
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path) if hash_files else None,
            **probe,
        }
        records.append(record)
    return records


def build_report(dataset_root: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    readable = [record for record in records if record["readable"] is True]
    durations = [record["duration_seconds"] for record in readable if record.get("duration_seconds")]
    fps_values = [record["fps"] for record in readable if record.get("fps")]
    resolutions = Counter(
        f"{record['width']}x{record['height']}"
        for record in readable
        if record.get("width") and record.get("height")
    )
    hashes: dict[str, list[str]] = defaultdict(list)
    filenames: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if record.get("sha256"):
            hashes[record["sha256"]].append(record["video_id"])
        filenames[Path(record["video_path"]).name].append(record["video_id"])
    duplicate_hashes = {key: value for key, value in hashes.items() if len(value) > 1}
    duplicate_filenames = {key: value for key, value in filenames.items() if len(value) > 1}
    class_counts = Counter(record["label_name"] for record in records)
    by_dataset = {
        name: {
            "total": sum(record["dataset"] == name for record in records),
            "real": sum(record["dataset"] == name and record["label"] == 0 for record in records),
            "fake": sum(record["dataset"] == name and record["label"] == 1 for record in records),
            "unknown": sum(record["dataset"] == name and record["label"] is None for record in records),
        }
        for name in sorted({record["dataset"] for record in records})
    }
    conflicting_hashes = {
        key: value
        for key, value in hashes.items()
        if len({record["label"] for record in records if record.get("sha256") == key}) > 1
    }
    return {
        "schema_version": 2,
        "dataset_root": str(dataset_root),
        "video_extensions": sorted(VIDEO_EXTENSIONS),
        "total_videos": len(records),
        "readable_videos": len(readable),
        "corrupted_or_unreadable_videos": len(records) - len(readable),
        "class_distribution": dict(class_counts),
        "videos_by_dataset": by_dataset,
        "videos_by_extension": dict(Counter(record["extension"] for record in records)),
        "duration_seconds": {
            "average": round(sum(durations) / len(durations), 3) if durations else None,
            "minimum": min(durations) if durations else None,
            "maximum": max(durations) if durations else None,
        },
        "average_fps": round(sum(fps_values) / len(fps_values), 3) if fps_values else None,
        "resolution_distribution": dict(resolutions),
        "duplicate_filenames": duplicate_filenames,
        "duplicate_hashes": duplicate_hashes,
        "conflicting_duplicate_hashes": conflicting_hashes,
        "source_grouping": {
            "available": False,
            "reason": "The dataset is flat and contains no identity/source metadata or source subdirectories.",
        },
        "records": records,
    }

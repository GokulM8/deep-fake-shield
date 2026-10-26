"""Build colab_bundle.zip for the hybrid temporal notebook.

The bundle root mirrors the repository, so the same scripts run unchanged in Colab:

    datasets/raw/<dataset>/<file>.mp4    labeled videos referenced by the split CSVs (unless --no-videos)
    artifacts/splits/{train,val,test}.csv  video_path rewritten relative to the bundle root
    artifacts/evaluations/baseline_f16/    cached baseline predictions (embedding sanity reference)
    models/deepfake_shield_video_v1.pt
    ml/**.py, backend/app/services/video_detector.py (+ package __init__ files)
    scripts/{evaluate_full,extract_embeddings,train_temporal_embeddings,make_ablation_table}.py
    notebooks/hybrid_temporal_colab.ipynb
    BUNDLE_MANIFEST.json

macOS ``._*`` AppleDouble files, ``.DS_Store`` and ``__pycache__`` are never included.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_full import local_path  # noqa: E402
from extract_embeddings import relative_video_path  # noqa: E402

SPLITS = ("train", "val", "test")
CODE_FILES = [
    "backend/app/__init__.py",
    "backend/app/services/__init__.py",
    "backend/app/services/video_detector.py",
    "scripts/evaluate_full.py",
    "scripts/extract_embeddings.py",
    "scripts/train_temporal_embeddings.py",
    "scripts/make_ablation_table.py",
    "notebooks/hybrid_temporal_colab.ipynb",
    "models/deepfake_shield_video_v1.pt",
    "artifacts/evaluations/baseline_f16/metrics.json",
    "artifacts/evaluations/baseline_f16/run_config.json",
    "artifacts/evaluations/baseline_f16/predictions_val.csv",
    "artifacts/evaluations/baseline_f16/predictions_test.csv",
]
STORED_SUFFIXES = {".mp4", ".pt", ".png"}  # already compressed; deflating them only costs time


def excluded(path: Path) -> bool:
    return any(part.startswith("._") or part in {".DS_Store", "__pycache__"} for part in path.parts)


def ml_files() -> list[str]:
    # ml/training holds the legacy script and the original training notebook; neither is needed.
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "ml").rglob("*.py")
        if not excluded(path.relative_to(ROOT)) and "training" not in path.relative_to(ROOT).parts
    )


def rewritten_split(split: str) -> tuple[bytes, list[str]]:
    with (ROOT / "artifacts/splits" / f"{split}.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows, fields = list(reader), reader.fieldnames
    for row in rows:
        row["video_path"] = relative_video_path(row["video_path"])
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8"), [row["video_path"] for row in rows]


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=ROOT / "colab_bundle.zip")
    parser.add_argument("--video-root", type=Path, default=ROOT / "datasets/raw")
    parser.add_argument("--no-videos", action="store_true",
                        help="Leave videos out (point the notebook at a dataset copy already on Drive)")
    args = parser.parse_args()

    splits, videos = {}, []
    for split in SPLITS:
        splits[split], paths = rewritten_split(split)
        videos.extend(paths)
    missing = [path for path in videos if not local_path(path, args.video_root).is_file()]
    if missing and not args.no_videos:
        print(f"{len(missing)} split videos are missing under {args.video_root}, e.g. {missing[:3]}", file=sys.stderr)
        return 1

    code = CODE_FILES + ml_files()
    absent = [path for path in code if not (ROOT / path).is_file()]
    if absent:
        print(f"Missing bundle files: {absent}", file=sys.stderr)
        return 1

    manifest = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "videos_included": not args.no_videos,
        "videos": len(videos),
        "split_sizes": {split: data.count(b"\n") - 1 for split, data in splits.items()},
        "code_files": code,
    }
    partial = args.output.with_suffix(".zip.partial")
    total_videos = 0 if args.no_videos else len(videos)
    with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as bundle:
        for split, data in splits.items():
            bundle.writestr(f"artifacts/splits/{split}.csv", data)
        for path in code:
            compression = zipfile.ZIP_STORED if Path(path).suffix in STORED_SUFFIXES else zipfile.ZIP_DEFLATED
            bundle.write(ROOT / path, path, compress_type=compression)
        if not args.no_videos:
            for done, path in enumerate(videos, start=1):
                bundle.write(local_path(path, args.video_root), path, compress_type=zipfile.ZIP_STORED)
                if done % 500 == 0 or done == total_videos:
                    print(f"videos {done}/{total_videos}", flush=True)
        bundle.writestr("BUNDLE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    partial.replace(args.output)

    with zipfile.ZipFile(args.output) as bundle:
        names = bundle.namelist()
    leaked = [name for name in names if excluded(Path(name))]
    if leaked:
        print(f"Refusing to ship AppleDouble/system files: {leaked[:5]}", file=sys.stderr)
        args.output.unlink()
        return 1
    size = args.output.stat().st_size
    print(f"Wrote {args.output} ({size / 1024**3:.2f} GiB, {size:,} bytes): {len(names)} entries, "
          f"{total_videos} videos, {len(code)} code/model files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Extract frozen EfficientNet-B0 frame embeddings for the hybrid temporal model.

Every video is read through the served preprocessing (``sample_faces`` / ``build_transform`` from
the backend VideoDetector): N evenly spaced frames, the largest Haar face crop with a 20% margin,
224x224, ImageNet normalization. Frames without a face are masked, not replaced. For each split
this writes ``<out-dir>/<split>.npz`` holding:

    embeddings   float16 [videos, N, 1280]  pooled backbone output (zeros where masked)
    mask         bool    [videos, N]        True where the frame has a detected face
    frame_probs  float32 [videos, N]        baseline fake probability per frame (NaN where masked)
    labels       int64   [videos]           0 real, 1 fake
    paths        str     [videos]           path relative to the bundle root (datasets/raw/...)
    sha256, errors       str [videos]       split grouping key; decode error ('' when none)

Work is saved in shards so an interrupted Colab session resumes where it stopped.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.services.video_detector import (  # noqa: E402
    FaceCropper,
    VideoDetector,
    VideoInferenceError,
    build_transform,
    embed_and_score,
    sample_faces,
)
from evaluate_full import file_sha256, local_path, resolve_device, stratified_subset  # noqa: E402

SPLITS = ("train", "val", "test")
EMBEDDING_DIM = 1280
SANITY_TOLERANCE = 1e-3


def relative_video_path(recorded: str) -> str:
    """``.../datasets/raw/<dataset>/<file>`` -> ``datasets/raw/<dataset>/<file>``, the bundle-relative key."""
    parts = Path(recorded).parts
    for index in range(len(parts) - 1):
        if parts[index : index + 2] == ("datasets", "raw"):
            return Path(*parts[index:]).as_posix()
    return Path(recorded).as_posix()


def read_split(splits_dir: Path, split: str) -> list[dict[str, str]]:
    with (splits_dir / f"{split}.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class FaceCropDataset(Dataset[dict[str, Any]]):
    """Decodes and face-crops one video per item on a DataLoader worker (CPU-bound part)."""

    def __init__(self, rows: list[dict[str, str]], video_root: Path, frames: int) -> None:
        self.rows, self.video_root, self.frames = rows, video_root, frames
        self.transform = build_transform()
        self.cropper: FaceCropper | None = None  # cv2 cascades cannot be pickled; build per worker

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        if self.cropper is None:
            self.cropper = FaceCropper()
        path = local_path(self.rows[index]["video_path"], self.video_root)
        try:
            sampled = sample_faces(path, self.frames, self.cropper, self.transform)
        except VideoInferenceError as error:
            return {"index": index, "images": None, "slots": [], "error": str(error)}
        images = torch.stack(sampled.images) if sampled.images else None
        return {"index": index, "images": images, "slots": sampled.slots, "error": ""}


def keep_list(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return batch


@dataclass
class Extracted:
    embeddings: np.ndarray
    mask: np.ndarray
    frame_probs: np.ndarray
    errors: list[str]


def extract_rows(
    model: torch.nn.Module,
    rows: list[dict[str, str]],
    video_root: Path,
    frames: int,
    device: torch.device,
    autocast: bool,
    workers: int,
    videos_per_batch: int,
    log_prefix: str = "",
) -> Extracted:
    count = len(rows)
    out = Extracted(
        embeddings=np.zeros((count, frames, EMBEDDING_DIM), dtype=np.float16),
        mask=np.zeros((count, frames), dtype=bool),
        frame_probs=np.full((count, frames), np.nan, dtype=np.float32),
        errors=[""] * count,
    )
    loader = DataLoader(
        FaceCropDataset(rows, video_root, frames),
        batch_size=videos_per_batch,
        num_workers=workers,
        collate_fn=keep_list,
        persistent_workers=False,
    )
    use_autocast = autocast and device.type == "cuda"
    started, done = time.monotonic(), 0
    for items in loader:
        crops = [item for item in items if item["images"] is not None]
        for item in items:
            out.errors[item["index"]] = item["error"]
        if crops:
            batch = torch.cat([item["images"] for item in crops]).to(device, non_blocking=True)
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16, enabled=use_autocast):
                embeddings, probabilities = embed_and_score(model, batch)
            embeddings = embeddings.float().cpu().numpy()
            probabilities = probabilities.float().cpu().numpy()
            offset = 0
            for item in crops:
                slots = np.asarray(item["slots"])
                taken = slice(offset, offset + len(slots))
                out.embeddings[item["index"], slots] = embeddings[taken].astype(np.float16)
                out.frame_probs[item["index"], slots] = probabilities[taken]
                out.mask[item["index"], slots] = True
                offset += len(slots)
        done += len(items)
        if log_prefix and (done % 200 < len(items) or done == count):
            elapsed = time.monotonic() - started
            print(f"{log_prefix} {done}/{count}  {elapsed / 60:.1f} min, ~{elapsed / done * (count - done) / 60:.1f} min left",
                  flush=True)
    return out


def load_backbone(checkpoint: Path, device: torch.device) -> torch.nn.Module:
    detector = VideoDetector(model_path=checkpoint, device=device)
    if detector.model is None:
        raise SystemExit(f"Model loading failed: {detector.load_error}")
    return detector.model


def extract_split(
    model: torch.nn.Module, split: str, args: argparse.Namespace, device: torch.device
) -> Path:
    target = args.out_dir / f"{split}.npz"
    if target.is_file():
        print(f"[{split}] {target} exists, skipping")
        return target
    rows = stratified_subset(read_split(args.splits_dir, split), args.limit)
    shard_dir = args.out_dir / f"{split}_parts"
    shard_dir.mkdir(parents=True, exist_ok=True)
    shard_paths = []
    for shard, start in enumerate(range(0, len(rows), args.shard_size)):
        shard_path = shard_dir / f"part_{shard:04d}.npz"
        shard_paths.append(shard_path)
        if shard_path.is_file():
            continue
        chunk = rows[start : start + args.shard_size]
        extracted = extract_rows(model, chunk, args.video_root, args.frames, device, not args.no_autocast,
                                 args.workers, args.videos_per_batch,
                                 log_prefix=f"[{split} shard {shard}] ")
        partial = shard_path.with_suffix(".tmp.npz")
        np.savez(partial, embeddings=extracted.embeddings, mask=extracted.mask,
                 frame_probs=extracted.frame_probs, errors=np.array(extracted.errors))
        partial.replace(shard_path)

    shards = [np.load(path) for path in shard_paths]
    partial = target.with_suffix(".tmp.npz")
    np.savez(
        partial,
        embeddings=np.concatenate([shard["embeddings"] for shard in shards]),
        mask=np.concatenate([shard["mask"] for shard in shards]),
        frame_probs=np.concatenate([shard["frame_probs"] for shard in shards]),
        errors=np.concatenate([shard["errors"] for shard in shards]),
        labels=np.array([int(row["label"]) for row in rows], dtype=np.int64),
        paths=np.array([relative_video_path(row["video_path"]) for row in rows]),
        sha256=np.array([row.get("sha256") or row["video_id"] for row in rows]),
    )
    partial.replace(target)
    with np.load(target) as saved:
        valid = saved["mask"].sum(axis=1)
        print(f"[{split}] wrote {target}: {len(valid)} videos, {int((valid == 0).sum())} with no face, "
              f"mean {valid.mean():.2f} valid frames")
    return target


def sanity_check(
    model: torch.nn.Module, args: argparse.Namespace, device: torch.device, reference: Path, videos: int = 20
) -> float:
    """Re-score ``videos`` val videos here and compare with the cached baseline predictions.

    Raises SystemExit when any video's mean frame probability differs by more than 1e-3 or the
    number of face frames differs, since then the embeddings would not match the served model."""
    with reference.open(newline="", encoding="utf-8") as handle:
        cached = {relative_video_path(row["video_path"]): row for row in csv.DictReader(handle)}
    rows = stratified_subset(read_split(args.splits_dir, "val"), videos)
    extracted = extract_rows(model, rows, args.video_root, args.frames, device, not args.no_autocast,
                             args.workers, args.videos_per_batch)
    worst, failures = 0.0, []
    for index, row in enumerate(rows):
        expected = cached[relative_video_path(row["video_path"])]
        valid = int(extracted.mask[index].sum())
        if valid != int(expected["n_valid_frames"]):
            failures.append(f"{row['video_id']}: {valid} face frames here vs {expected['n_valid_frames']} cached")
            continue
        if not valid:
            continue
        difference = abs(float(np.nanmean(extracted.frame_probs[index])) - float(expected["fake_prob"]))
        worst = max(worst, difference)
        if difference > SANITY_TOLERANCE:
            failures.append(f"{row['video_id']}: |diff| {difference:.2e}")
    status = "PASS" if not failures else "FAIL"
    print(f"Sanity check {status}: {len(rows)} val videos, max |mean prob - baseline_f16| = {worst:.2e} "
          f"(tolerance {SANITY_TOLERANCE:g}, autocast {'on' if not args.no_autocast and device.type == 'cuda' else 'off'})")
    if failures:
        print("\n".join(f"  {line}" for line in failures))
        raise SystemExit("Embeddings do not match the served baseline; stop and investigate before extracting.")
    return worst


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", type=Path, default=ROOT / "models/deepfake_shield_video_v1.pt")
    parser.add_argument("--splits-dir", type=Path, default=ROOT / "artifacts/splits")
    parser.add_argument("--video-root", type=Path, default=ROOT / "datasets/raw")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--workers", type=int, default=2, help="DataLoader workers decoding and face-cropping")
    parser.add_argument("--videos-per-batch", type=int, default=8, help="Videos per GPU batch (x frames crops)")
    parser.add_argument("--shard-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=0, help="Class-stratified subset per split, for quick checks")
    parser.add_argument("--no-autocast", action="store_true", help="Run the backbone in fp32 on CUDA")
    parser.add_argument("--splits", nargs="+", default=list(SPLITS), choices=SPLITS)
    parser.add_argument("--sanity-reference", type=Path,
                        default=ROOT / "artifacts/evaluations/baseline_f16/predictions_val.csv")
    parser.add_argument("--sanity-only", action="store_true")
    parser.add_argument("--skip-sanity", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    device = resolve_device(args.device)
    model = load_backbone(args.checkpoint, device)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if not args.skip_sanity:
        if args.frames != 16:
            raise SystemExit("The sanity reference is baseline_f16; use --frames 16 or --skip-sanity.")
        sanity = sanity_check(model, args, device, args.sanity_reference)
    if args.sanity_only:
        return 0
    meta_path = args.out_dir / "meta.json"
    meta = {
        "checkpoint": args.checkpoint.name,
        "checkpoint_sha256": file_sha256(args.checkpoint),
        "frames": args.frames,
        "embedding_dim": EMBEDDING_DIM,
        "embedding": "EfficientNet-B0 features -> global average pool (classifier input), frozen, eval mode",
        "preprocessing": "backend sample_faces + build_transform (linspace sampling, Haar face crop 20% margin, "
                         "224x224, ImageNet norm); no-face frames masked",
        "device": str(device),
        "autocast_fp16": not args.no_autocast and device.type == "cuda",
        "limit": args.limit or None,
    }
    if meta_path.is_file():
        previous = json.loads(meta_path.read_text())
        changed = {key for key in ("checkpoint_sha256", "frames", "limit", "autocast_fp16") if previous.get(key) != meta[key]}
        if changed:
            raise SystemExit(f"{args.out_dir} holds embeddings made with different {sorted(changed)}; use another --out-dir.")
        meta["created_at"] = previous["created_at"]
    else:
        meta["created_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    if not args.skip_sanity:
        meta["sanity_max_abs_diff"] = sanity
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    for split in args.splits:
        extract_split(model, split, args, device)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

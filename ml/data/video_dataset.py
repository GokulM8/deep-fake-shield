"""Lazy video-frame dataset with deterministic sampling and face crops."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset


def sample_frame_indices(frame_count: int, count: int) -> np.ndarray:
    if frame_count <= 0:
        return np.zeros(count, dtype=np.int64)
    return np.linspace(0, max(frame_count - 1, 0), count, dtype=np.int64)


class FaceCropper:
    def __init__(self, margin: float = 0.2) -> None:
        self.margin = margin
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.detector = cv2.CascadeClassifier(cascade_path)

    def crop(self, frame: np.ndarray) -> np.ndarray | None:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(32, 32))
        if len(faces) == 0:
            return None
        x, y, width, height = max(faces, key=lambda box: int(box[2]) * int(box[3]))
        pad_x, pad_y = int(width * self.margin), int(height * self.margin)
        top, bottom = max(0, y - pad_y), min(frame.shape[0], y + height + pad_y)
        left, right = max(0, x - pad_x), min(frame.shape[1], x + width + pad_x)
        return frame[top:bottom, left:right]


class VideoFrameDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    def __init__(self, csv_path: Path, frames_per_video: int = 4, transform: Any = None, video_root: Path | None = None) -> None:
        with csv_path.open(newline="", encoding="utf-8") as csv_file:
            self.records = list(csv.DictReader(csv_file))
        self.frames_per_video = frames_per_video
        self.transform = transform
        self.video_root = video_root
        self.cropper = FaceCropper()

    def resolve_video_path(self, path: str) -> Path:
        original = Path(path)
        if original.exists() or self.video_root is None:
            return original
        marker = Path("datasets/raw")
        try:
            relative = Path(*original.parts[original.parts.index(marker.parts[0]) :])
            marker_index = next(index for index in range(len(original.parts) - 1) if Path(*original.parts[index : index + 2]) == marker)
            relative = Path(*original.parts[marker_index + len(marker.parts) :])
            candidate = self.video_root / relative
            if candidate.exists():
                return candidate
        except (ValueError, StopIteration):
            pass
        candidate = self.video_root / original.name
        return candidate if candidate.exists() else original

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        record = self.records[index]
        capture = cv2.VideoCapture(str(self.resolve_video_path(record["video_path"])))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frames = []
        for frame_index in sample_frame_indices(frame_count, self.frames_per_video):
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
            ok, frame = capture.read()
            if not ok:
                continue
            crop = self.cropper.crop(frame)
            image = crop if crop is not None else frame
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(image))
        capture.release()
        if not frames:
            frames = [Image.fromarray(np.zeros((224, 224, 3), dtype=np.uint8))]
        if self.transform is not None:
            tensors = [self.transform(frame) for frame in frames]
        else:
            tensors = [torch.from_numpy(np.asarray(frame)).permute(2, 0, 1).float() / 255 for frame in frames]
        tensors = [
            torch.from_numpy(np.array(frame, copy=True)).permute(2, 0, 1).float() / 255
            if not isinstance(frame, torch.Tensor)
            else frame
            for frame in tensors
        ]
        while len(tensors) < self.frames_per_video:
            tensors.append(tensors[-1].clone())
        return torch.stack(tensors[: self.frames_per_video]), torch.tensor(int(record["label"]), dtype=torch.long)

"""EfficientNet-B0 video inference for the production analysis endpoint."""

from __future__ import annotations

import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ML_ROOT = PROJECT_ROOT / "ml"
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from data.video_dataset import FaceCropper, sample_frame_indices  # noqa: E402
from models.efficientnet_baseline import build_model  # noqa: E402

DEFAULT_THRESHOLD = 0.5
DEFAULT_FRAMES = 2
MODEL_FILENAME = "deepfake_shield_video_v1.pt"
ARTIFACT_MAX_WIDTH = 640


class VideoInferenceError(RuntimeError):
    """Raised when a video cannot be analyzed by the trained detector."""


@dataclass
class SampledFaces:
    """Face crops from evenly sampled frames, plus the video metadata read alongside them."""

    frame_count: int
    fps: float
    width: int
    height: int
    images: list[torch.Tensor]
    frame_indices: list[int]
    frames: list[np.ndarray]
    boxes: list[tuple[int, int, int, int]]


class VideoDetector:
    def __init__(
        self,
        model_path: Path | None = None,
        threshold: float = DEFAULT_THRESHOLD,
        frames: int = DEFAULT_FRAMES,
        device: torch.device | None = None,
    ) -> None:
        self.model_path = model_path or Path(
            os.getenv("DEEPFAKE_MODEL_PATH", str(PROJECT_ROOT / "models" / MODEL_FILENAME))
        )
        self.threshold = threshold
        self.frames = frames
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        self.cropper = FaceCropper()
        # The Grad-CAM hook lives on the shared model and the Haar cascade is not thread-safe,
        # so concurrent analyses must not interleave.
        self._lock = threading.Lock()
        self.model: torch.nn.Module | None = None
        self.load_error: Exception | None = None
        try:
            self.model = self._load_model()
        except Exception as error:  # surface a useful failed analysis instead of breaking app import
            self.load_error = error

    def _load_model(self) -> torch.nn.Module:
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Model checkpoint not found: {self.model_path}")
        model = build_model(pretrained=False).to(self.device)
        checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)
        state_dict = checkpoint.get("model_state_dict", checkpoint)
        model.load_state_dict(state_dict)
        model.eval()
        return model

    def predict(self, video_path: Path, artifact_dir: Path | None = None) -> dict[str, Any]:
        """Score sampled frames; with ``artifact_dir``, also write ``frame_<id>.jpg`` and
        ``heatmap_<id>.jpg`` (Grad-CAM over the face crop) for each analyzed frame."""
        with self._lock:
            return self._predict(video_path, artifact_dir)

    def score_frames(self, video_path: Path) -> list[float]:
        """Per-frame fake probabilities over the served preprocessing, without Grad-CAM.

        Returns an empty list when no sampled frame has a detectable face. Scores equal the
        ``predict`` frame scores; this path only skips the backward pass, for bulk evaluation."""
        with self._lock:
            sampled = self._sample_faces(video_path)
            if not sampled.images:
                return []
            assert self.model is not None
            with torch.no_grad():
                logits = self.model(torch.stack(sampled.images).to(self.device))
            return torch.softmax(logits, dim=1)[:, 1].cpu().tolist()

    def _sample_faces(self, video_path: Path) -> SampledFaces:
        if self.load_error is not None or self.model is None:
            detail = str(self.load_error) if self.load_error else "Model is not loaded"
            raise VideoInferenceError(f"Model loading failed: {detail}")

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            capture.release()
            raise VideoInferenceError("Uploaded video cannot be opened")

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if frame_count <= 0:
            capture.release()
            raise VideoInferenceError("Uploaded video contains no readable frames")

        sampled = SampledFaces(frame_count, fps, width, height, [], [], [], [])
        for frame_index in sample_frame_indices(frame_count, self.frames):
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
            ok, frame = capture.read()
            if not ok:
                continue
            box = self.cropper.locate(frame)
            if box is None:
                continue
            left, top, right, bottom = box
            rgb = cv2.cvtColor(frame[top:bottom, left:right], cv2.COLOR_BGR2RGB)
            sampled.images.append(self.transform(Image.fromarray(rgb)))
            sampled.frame_indices.append(int(frame_index))
            sampled.frames.append(frame)
            sampled.boxes.append(box)
        capture.release()
        return sampled

    def _predict(self, video_path: Path, artifact_dir: Path | None) -> dict[str, Any]:
        sampled = self._sample_faces(video_path)
        if not sampled.images:
            raise VideoInferenceError("No detectable face was found in the sampled video frames")

        fps = sampled.fps
        batch = torch.stack(sampled.images).to(self.device)
        probabilities, cams = self._predict_with_gradcam(batch)
        if artifact_dir is not None:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            for frame_index, frame, box, cam in zip(sampled.frame_indices, sampled.frames, sampled.boxes, cams):
                _write_frame_artifacts(artifact_dir, frame_index, frame, box, cam)
        fake_probability = float(np.mean(probabilities))
        real_probability = 1.0 - fake_probability
        prediction = "FAKE" if fake_probability >= self.threshold else "REAL"
        confidence = fake_probability if prediction == "FAKE" else real_probability
        frame_scores = [
            {
                "frame_id": frame_index,
                "timestamp": round(frame_index / fps, 3) if fps else None,
                "fake_probability": round(float(probability), 6),
                "face_box": list(box),
            }
            for frame_index, probability, box in zip(sampled.frame_indices, probabilities, sampled.boxes)
        ]
        return {
            "prediction": prediction,
            "confidence": round(confidence, 6),
            "fake_probability": round(fake_probability, 6),
            "real_probability": round(real_probability, 6),
            "frames_analyzed": len(sampled.images),
            "duration_seconds": sampled.frame_count / fps if fps else None,
            "frame_rate": fps or None,
            "width": sampled.width or None,
            "height": sampled.height or None,
            "frame_scores": frame_scores,
        }

    def _predict_with_gradcam(self, batch: torch.Tensor) -> tuple[list[float], np.ndarray]:
        """Return per-image fake probabilities and Grad-CAM maps for the fake logit."""
        assert self.model is not None
        captured: dict[str, torch.Tensor] = {}

        def keep_activation(_module: torch.nn.Module, _inputs: Any, output: torch.Tensor) -> None:
            output.retain_grad()
            captured["activation"] = output

        handle = self.model.features[-1].register_forward_hook(keep_activation)
        try:
            logits = self.model(batch)
            self.model.zero_grad(set_to_none=True)
            # Eval-mode BatchNorm keeps samples independent, so one backward pass gives each its own map.
            logits[:, 1].sum().backward()
        finally:
            handle.remove()

        activation = captured["activation"]
        weights = activation.grad.mean(dim=(2, 3), keepdim=True)
        cams = torch.relu((weights * activation).sum(dim=1))
        peaks = cams.flatten(1).amax(dim=1).clamp_min(1e-8)[:, None, None]
        probabilities = torch.softmax(logits, dim=1)[:, 1].detach().cpu().tolist()
        return probabilities, (cams / peaks).detach().cpu().numpy()


def _write_frame_artifacts(
    artifact_dir: Path,
    frame_index: int,
    frame: np.ndarray,
    box: tuple[int, int, int, int],
    cam: np.ndarray,
) -> None:
    """Save the full frame and a same-sized heatmap (black outside the face crop) for overlaying."""
    left, top, right, bottom = box
    face_cam = cv2.resize(cam.astype(np.float32), (right - left, bottom - top), interpolation=cv2.INTER_CUBIC)
    face_cam = np.clip(face_cam, 0, 1)
    colored = cv2.applyColorMap((face_cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    heatmap = np.zeros_like(frame)
    # Fade by activation so weak regions stay dark and vanish under a screen blend.
    heatmap[top:bottom, left:right] = (colored * face_cam[..., None]).astype(np.uint8)

    height, width = frame.shape[:2]
    if width > ARTIFACT_MAX_WIDTH:
        size = (ARTIFACT_MAX_WIDTH, round(height * ARTIFACT_MAX_WIDTH / width))
        frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
        heatmap = cv2.resize(heatmap, size, interpolation=cv2.INTER_AREA)
    quality = [cv2.IMWRITE_JPEG_QUALITY, 85]
    cv2.imwrite(str(artifact_dir / f"frame_{frame_index}.jpg"), frame, quality)
    cv2.imwrite(str(artifact_dir / f"heatmap_{frame_index}.jpg"), heatmap, quality)

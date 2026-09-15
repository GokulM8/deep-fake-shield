"""EfficientNet-B0 video inference for the production analysis endpoint."""

from __future__ import annotations

import os
import sys
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


class VideoInferenceError(RuntimeError):
    """Raised when a video cannot be analyzed by the trained detector."""


class VideoDetector:
    def __init__(
        self,
        model_path: Path | None = None,
        threshold: float = DEFAULT_THRESHOLD,
        frames: int = DEFAULT_FRAMES,
    ) -> None:
        self.model_path = model_path or Path(
            os.getenv("DEEPFAKE_MODEL_PATH", str(PROJECT_ROOT / "models" / MODEL_FILENAME))
        )
        self.threshold = threshold
        self.frames = frames
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        self.cropper = FaceCropper()
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

    def predict(self, video_path: Path) -> dict[str, Any]:
        if self.load_error is not None or self.model is None:
            detail = str(self.load_error) if self.load_error else "Model is not loaded"
            raise VideoInferenceError(f"Model loading failed: {detail}")

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            capture.release()
            raise VideoInferenceError("Uploaded video cannot be opened")

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        if frame_count <= 0:
            capture.release()
            raise VideoInferenceError("Uploaded video contains no readable frames")

        images: list[torch.Tensor] = []
        frame_indices: list[int] = []
        for frame_index in sample_frame_indices(frame_count, self.frames):
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
            ok, frame = capture.read()
            if not ok:
                continue
            crop = self.cropper.crop(frame)
            if crop is None:
                continue
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            images.append(self.transform(Image.fromarray(rgb)))
            frame_indices.append(int(frame_index))
        capture.release()

        if not images:
            raise VideoInferenceError("No detectable face was found in the sampled video frames")

        batch = torch.stack(images).to(self.device)
        with torch.no_grad():
            probabilities = torch.softmax(self.model(batch), dim=1)[:, 1].cpu().tolist()
        fake_probability = float(np.mean(probabilities))
        real_probability = 1.0 - fake_probability
        prediction = "FAKE" if fake_probability >= self.threshold else "REAL"
        confidence = fake_probability if prediction == "FAKE" else real_probability
        frame_scores = [
            {
                "frame_id": frame_index,
                "timestamp": round(frame_index / fps, 3) if fps else None,
                "fake_probability": round(float(probability), 6),
            }
            for frame_index, probability in zip(frame_indices, probabilities)
        ]
        return {
            "prediction": prediction,
            "confidence": round(confidence, 6),
            "fake_probability": round(fake_probability, 6),
            "real_probability": round(real_probability, 6),
            "frames_analyzed": len(images),
            "frame_scores": frame_scores,
        }

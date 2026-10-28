"""EfficientNet-B0 video inference for the production analysis endpoint."""

from __future__ import annotations

import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

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
from models.video_heads import load_head  # noqa: E402

# 16 frames at the val-tuned threshold (artifacts/evaluations/baseline_f16) beat 2 frames on every
# test metric, and cost ~3.9 s per video with Grad-CAM on CPU (Apple M4).
DEFAULT_THRESHOLD = 0.3654
DEFAULT_FRAMES = 16
MODEL_FILENAME = "deepfake_shield_video_v1.pt"
# Video-level heads over the frozen backbone's 16-frame embeddings (Colab T4 run, see
# artifacts/evaluations/hybrid_colab); each checkpoint stores its val-tuned threshold.
HEAD_FILENAMES = {
    "mlp": "deepfake_shield_meanpool_mlp_v1.pt",
    "temporal": "deepfake_shield_temporal_v1.pt",
}
DEFAULT_MODEL = "mlp"
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
    # Position of each kept frame among the ``frames`` evenly spaced samples, so callers can
    # build a fixed-length sequence with a no-face mask.
    slots: list[int]


def build_transform() -> transforms.Compose:
    """Face-crop preprocessing shared by serving, evaluation and embedding extraction."""
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])


def sample_faces(video_path: Path, frames: int, cropper: FaceCropper, transform: Any) -> SampledFaces:
    """Read ``frames`` evenly spaced frames and keep the largest padded face crop of each.

    Frames that fail to decode or have no detectable face are skipped. Raises
    ``VideoInferenceError`` when the video cannot be opened or reports no frames."""
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

    sampled = SampledFaces(frame_count, fps, width, height, [], [], [], [], [])
    for slot, frame_index in enumerate(sample_frame_indices(frame_count, frames)):
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
        ok, frame = capture.read()
        if not ok:
            continue
        box = cropper.locate(frame)
        if box is None:
            continue
        left, top, right, bottom = box
        rgb = cv2.cvtColor(frame[top:bottom, left:right], cv2.COLOR_BGR2RGB)
        sampled.images.append(transform(Image.fromarray(rgb)))
        sampled.frame_indices.append(int(frame_index))
        sampled.frames.append(frame)
        sampled.boxes.append(box)
        sampled.slots.append(slot)
    capture.release()
    return sampled


def embed_and_score(model: torch.nn.Module, batch: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Pooled EfficientNet-B0 embeddings ([N, 1280]) and fake probabilities ([N]) for face crops.

    Mirrors ``EfficientNet.forward`` (features -> avgpool -> flatten -> classifier), so the
    probabilities equal ``softmax(model(batch))[:, 1]``."""
    embeddings = torch.flatten(model.avgpool(model.features(batch)), 1)
    logits = model.classifier(embeddings)
    return embeddings, torch.softmax(logits.float(), dim=1)[:, 1]


class VideoDetector:
    def __init__(
        self,
        model_path: Path | None = None,
        threshold: float | None = None,
        frames: int | None = None,
        device: torch.device | None = None,
    ) -> None:
        self.model_path = model_path or Path(
            os.getenv("DEEPFAKE_MODEL_PATH", str(PROJECT_ROOT / "models" / MODEL_FILENAME))
        )
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.transform = build_transform()
        self.cropper = FaceCropper()
        # The Grad-CAM hook lives on the shared model and the Haar cascade is not thread-safe,
        # so concurrent analyses must not interleave.
        self._lock = threading.Lock()
        self.model: torch.nn.Module | None = None
        self.load_error: Exception | None = None
        stored: dict[str, Any] = {}
        try:
            self.model = self._load_model()
            stored = self._load_extras()
        except Exception as error:  # surface a useful failed analysis instead of breaking app import
            self.load_error = error

        self.threshold: float | None = (
            threshold if threshold is not None
            else _env_float("DEEPFAKE_THRESHOLD", stored.get("threshold", self.default_threshold))
        )
        self.frames = frames if frames is not None else _env_int("DEEPFAKE_FRAMES", stored.get("frames", DEFAULT_FRAMES))
        if self.threshold is not None and not 0 < self.threshold < 1:
            raise ValueError(f"Decision threshold must be between 0 and 1, got {self.threshold}")
        if self.frames < 1:
            raise ValueError(f"Frames per video must be at least 1, got {self.frames}")
        if stored.get("frames") is not None and self.frames != stored["frames"]:
            # Embeddings fill fixed sampling slots and the threshold was tuned at this count.
            raise ValueError(f"The {self.name} head was trained on {stored['frames']} frames, got DEEPFAKE_FRAMES={self.frames}")

    name = "baseline"
    # Head detectors have no fallback: their threshold comes from the checkpoint or the environment.
    default_threshold: float | None = DEFAULT_THRESHOLD

    @property
    def frame_threshold(self) -> float | None:
        """Threshold for flagging individual frames by their frame-classifier score."""
        return self.threshold

    @property
    def inference_mode(self) -> str:
        return "efficientnet_b0_video"

    @property
    def signal_name(self) -> str:
        return "EfficientNet-B0 video model"

    @property
    def score_explanation(self) -> str:
        return f"Mean fake probability across detected faces in {self.frames} sampled frames"

    @property
    def provenance(self) -> str:
        return f"model checkpoint: {self.model_path.name}"

    def _load_extras(self) -> dict[str, Any]:
        """Load anything beyond the frame classifier; return stored ``threshold``/``frames`` defaults."""
        return {}

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

    def score_video(self, video_path: Path) -> float | None:
        """The served video fake probability, or None when no sampled frame has a face."""
        return self.score_video_detail(video_path)[0]

    def score_video_detail(self, video_path: Path) -> tuple[float | None, int]:
        """The served video fake probability (None without faces) and the number of face frames."""
        scores = self.score_frames(video_path)
        return (float(np.mean(scores)) if scores else None), len(scores)

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
        return sample_faces(video_path, self.frames, self.cropper, self.transform)

    def _predict(self, video_path: Path, artifact_dir: Path | None) -> dict[str, Any]:
        sampled = self._sample_faces(video_path)
        if not sampled.images:
            raise VideoInferenceError("No detectable face was found in the sampled video frames")

        fps = sampled.fps
        probabilities, fake_probability, cams = self._score_with_gradcam(sampled)
        if artifact_dir is not None:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            for frame_index, frame, box, cam in zip(sampled.frame_indices, sampled.frames, sampled.boxes, cams):
                _write_frame_artifacts(artifact_dir, frame_index, frame, box, cam)
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

    def _score_with_gradcam(self, sampled: SampledFaces) -> tuple[list[float], float, np.ndarray]:
        """Frame fake probabilities, the video fake probability and per-frame Grad-CAM maps."""
        probabilities, cams = self._predict_with_gradcam(torch.stack(sampled.images).to(self.device))
        return probabilities, float(np.mean(probabilities)), cams

    def _predict_with_gradcam(
        self, batch: torch.Tensor, frame_logits: Callable[[torch.Tensor], torch.Tensor] | None = None
    ) -> tuple[list[float], np.ndarray]:
        """Return per-image fake probabilities and Grad-CAM maps for the fake logit.

        ``frame_logits`` maps the face batch to per-image logits; it defaults to the frame classifier."""
        assert self.model is not None
        frame_logits = frame_logits or self.model
        captured: dict[str, torch.Tensor] = {}

        def keep_activation(_module: torch.nn.Module, _inputs: Any, output: torch.Tensor) -> None:
            output.retain_grad()
            captured["activation"] = output

        handle = self.model.features[-1].register_forward_hook(keep_activation)
        try:
            logits = frame_logits(batch)
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


class EmbeddingHeadDetector(VideoDetector):
    """The frame classifier as a frozen encoder, with a video-level head over its frame embeddings.

    Frame scores, Grad-CAM maps, frame images and face boxes all come from the backbone (its own
    classifier gives the frame-level scores); the video verdict comes from the head, at the head
    checkpoint's stored threshold unless DEEPFAKE_THRESHOLD overrides it.
    """

    default_threshold = None
    _LABELS = {
        "mlp": ("efficientnet_b0_meanpool_mlp", "EfficientNet-B0 + MLP head"),
        "temporal": ("efficientnet_b0_temporal_transformer", "EfficientNet-B0 + Transformer head"),
    }

    def __init__(self, kind: str, head_path: Path | None = None, **kwargs: Any) -> None:
        if kind not in HEAD_FILENAMES:
            raise ValueError(f"Unknown head {kind!r}; expected one of {sorted(HEAD_FILENAMES)}")
        self.name = kind
        self.head_path = head_path or Path(
            os.getenv("DEEPFAKE_HEAD_PATH", str(PROJECT_ROOT / "models" / HEAD_FILENAMES[kind]))
        )
        self.head: torch.nn.Module | None = None
        super().__init__(**kwargs)

    @property
    def frame_threshold(self) -> float | None:
        # Frame scores come from the backbone classifier, so flag them at its own tuned threshold,
        # not at the head's (which lives on a different, far less calibrated scale).
        return DEFAULT_THRESHOLD

    @property
    def inference_mode(self) -> str:
        return self._LABELS[self.name][0]

    @property
    def signal_name(self) -> str:
        return self._LABELS[self.name][1]

    @property
    def score_explanation(self) -> str:
        return (f"Video-level head score over embeddings of detected faces in {self.frames} sampled frames "
                "(frame scores come from the frame classifier)")

    @property
    def provenance(self) -> str:
        return f"model checkpoints: {self.model_path.name} (frame encoder), {self.head_path.name} (head)"

    def _load_extras(self) -> dict[str, Any]:
        if not self.head_path.is_file():
            raise FileNotFoundError(f"Head checkpoint not found: {self.head_path}")
        self.head, checkpoint = load_head(self.head_path, self.device)
        encoder = checkpoint.get("encoder_checkpoint")
        if encoder and encoder != self.model_path.name:
            raise ValueError(f"{self.head_path.name} was trained on {encoder}, not {self.model_path.name}")
        return {"threshold": float(checkpoint["threshold"]), "frames": int(checkpoint["n_frames"])}

    def score_video_detail(self, video_path: Path) -> tuple[float | None, int]:
        """The head's video fake probability (None without faces) and the number of face frames."""
        with self._lock:
            sampled = self._sample_faces(video_path)
            if not sampled.images:
                return None, 0
            assert self.model is not None
            with torch.no_grad():
                embeddings, _ = embed_and_score(self.model, torch.stack(sampled.images).to(self.device))
                return self._head_probability(sampled.slots, embeddings), len(sampled.images)

    def _score_with_gradcam(self, sampled: SampledFaces) -> tuple[list[float], float, np.ndarray]:
        assert self.model is not None
        captured: dict[str, torch.Tensor] = {}

        def frame_logits(batch: torch.Tensor) -> torch.Tensor:
            # One backbone pass yields both the embeddings for the head and the frame logits for Grad-CAM.
            captured["embeddings"] = torch.flatten(self.model.avgpool(self.model.features(batch)), 1)
            return self.model.classifier(captured["embeddings"])

        probabilities, cams = self._predict_with_gradcam(torch.stack(sampled.images).to(self.device), frame_logits)
        with torch.no_grad():
            video_probability = self._head_probability(sampled.slots, captured["embeddings"].detach())
        return probabilities, video_probability, cams

    def _head_probability(self, slots: list[int], embeddings: torch.Tensor) -> float:
        """Place each face embedding in its sampling slot (no-face slots stay zero and masked out)."""
        assert self.head is not None
        index = torch.tensor(slots, device=self.device)
        x = torch.zeros(1, self.frames, embeddings.shape[1], device=self.device)
        x[0, index] = embeddings.float()
        mask = torch.zeros(1, self.frames, dtype=torch.bool, device=self.device)
        mask[0, index] = True
        logits = self.head(x, mask)
        return float(torch.softmax(logits.float(), dim=1)[0, 1])


def create_detector(kind: str | None = None, **kwargs: Any) -> VideoDetector:
    """The serving detector named by ``kind`` or ``DEEPFAKE_MODEL``: mlp (default), temporal or baseline."""
    kind = (kind or os.getenv("DEEPFAKE_MODEL") or DEFAULT_MODEL).strip().lower()
    if kind == "baseline":
        return VideoDetector(**kwargs)
    if kind in HEAD_FILENAMES:
        return EmbeddingHeadDetector(kind, **kwargs)
    raise ValueError(f"DEEPFAKE_MODEL must be one of baseline, {', '.join(HEAD_FILENAMES)}; got {kind!r}")


def _env_float(name: str, default: float | None) -> float | None:
    value = os.getenv(name)
    try:
        return float(value) if value else default
    except ValueError:
        raise ValueError(f"{name} must be a number, got {value!r}") from None


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    try:
        return int(value) if value else default
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {value!r}") from None


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

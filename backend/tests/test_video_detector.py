import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from app.services.video_detector import (
    DEFAULT_THRESHOLD,
    HEAD_FILENAMES,
    EmbeddingHeadDetector,
    VideoDetector,
    VideoInferenceError,
    create_detector,
)
from models.video_heads import MeanPoolMLP, TemporalHead, load_head


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_VIDEO = ROOT / "datasets/raw/test/00272.mp4"
HEAD_PATHS = {kind: ROOT / "models" / name for kind, name in HEAD_FILENAMES.items()}


def needs_head(kind: str) -> pytest.MarkDecorator:
    return pytest.mark.skipif(not HEAD_PATHS[kind].is_file(), reason=f"head checkpoint missing: {HEAD_PATHS[kind]}")


def test_model_loads_on_cpu() -> None:
    detector = VideoDetector()
    assert detector.model is not None
    assert detector.device.type == "cpu"
    assert not detector.model.training


def test_face_extraction_matches_training_preprocessing() -> None:
    detector = VideoDetector()
    capture = cv2.VideoCapture(str(SAMPLE_VIDEO))
    ok, frame = capture.read()
    capture.release()
    assert ok
    crop = detector.cropper.crop(frame)
    assert crop is not None
    tensor = detector.transform(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))
    assert tuple(tensor.shape) == (3, 224, 224)


def test_real_video_inference_returns_expected_contract() -> None:
    detector = VideoDetector()
    result = detector.predict(SAMPLE_VIDEO)
    assert result["prediction"] in {"REAL", "FAKE"}
    assert 0 <= result["confidence"] <= 1
    assert 0 <= result["fake_probability"] <= 1
    assert 1 <= result["frames_analyzed"] <= detector.frames
    assert (result["prediction"] == "FAKE") == (result["fake_probability"] >= detector.threshold)


def test_serving_defaults_to_16_frames_at_tuned_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPFAKE_FRAMES", raising=False)
    monkeypatch.delenv("DEEPFAKE_THRESHOLD", raising=False)
    detector = VideoDetector()
    assert (detector.frames, detector.threshold) == (16, 0.3654)


def test_frames_and_threshold_come_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPFAKE_FRAMES", "2")
    monkeypatch.setenv("DEEPFAKE_THRESHOLD", "0.2431")
    detector = VideoDetector()
    assert (detector.frames, detector.threshold) == (2, 0.2431)


@pytest.mark.parametrize(("name", "value"), [("DEEPFAKE_FRAMES", "0"), ("DEEPFAKE_FRAMES", "two"), ("DEEPFAKE_THRESHOLD", "1.5")])
def test_invalid_serving_config_is_rejected(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=r"DEEPFAKE_FRAMES|threshold|Frames"):
        VideoDetector()


def test_video_without_detectable_face_fails_cleanly(tmp_path: Path) -> None:
    path = tmp_path / "blank.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 5, (64, 64))
    for _ in range(2):
        writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
    writer.release()
    with pytest.raises(VideoInferenceError, match="No detectable face"):
        VideoDetector().predict(path)

def test_inference_writes_frame_and_gradcam_artifacts(tmp_path: Path) -> None:
    result = VideoDetector().predict(SAMPLE_VIDEO, artifact_dir=tmp_path)
    for score in result["frame_scores"]:
        left, top, right, bottom = score["face_box"]
        assert 0 <= left < right and 0 <= top < bottom
        frame = cv2.imread(str(tmp_path / f"frame_{score['frame_id']}.jpg"))
        heatmap = cv2.imread(str(tmp_path / f"heatmap_{score['frame_id']}.jpg"))
        assert frame is not None and heatmap is not None
        assert frame.shape == heatmap.shape
        assert heatmap.max() > 0


@pytest.mark.skipif(not SAMPLE_VIDEO.is_file(), reason=f"local test video missing: {SAMPLE_VIDEO}")
def test_concurrent_predictions_are_safe_and_identical(tmp_path: Path) -> None:
    detector = VideoDetector()
    start = threading.Barrier(4)

    def run(worker: int) -> float:
        start.wait()
        return detector.predict(SAMPLE_VIDEO, artifact_dir=tmp_path / str(worker))["fake_probability"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        scores = list(pool.map(run, range(4)))

    assert scores == pytest.approx([scores[0]] * 4, abs=1e-6)


@pytest.mark.skipif(not SAMPLE_VIDEO.is_file(), reason=f"local test video missing: {SAMPLE_VIDEO}")
def test_score_frames_matches_served_frame_scores() -> None:
    detector = VideoDetector()
    served = [score["fake_probability"] for score in detector.predict(SAMPLE_VIDEO)["frame_scores"]]
    # Served scores are rounded to 6 decimals and the Grad-CAM pass differs from no_grad at float32 noise.
    assert detector.score_frames(SAMPLE_VIDEO) == pytest.approx(served, abs=1e-5)


@pytest.mark.parametrize(("kind", "head_class", "has_best_epoch"), [
    pytest.param("mlp", MeanPoolMLP, False, marks=needs_head("mlp")),
    pytest.param("temporal", TemporalHead, True, marks=needs_head("temporal")),
])
def test_head_checkpoints_load_strictly(kind: str, head_class: type, has_best_epoch: bool) -> None:
    head, checkpoint = load_head(HEAD_PATHS[kind])
    assert isinstance(head, head_class) and not head.training
    assert (checkpoint["n_frames"], checkpoint["embed_dim"]) == (16, 1280)
    assert checkpoint["encoder_checkpoint"] == "deepfake_shield_video_v1.pt"
    assert 0 < checkpoint["threshold"] < 1
    assert ("best_epoch" in checkpoint) == has_best_epoch


def test_serving_defaults_to_mlp_head(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPFAKE_MODEL", raising=False)
    detector = create_detector()
    assert isinstance(detector, EmbeddingHeadDetector) and detector.name == "mlp"


@pytest.mark.parametrize("kind", ["mlp", "temporal"])
def test_head_uses_its_stored_threshold_unless_overridden(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    if not HEAD_PATHS[kind].is_file():
        pytest.skip(f"head checkpoint missing: {HEAD_PATHS[kind]}")
    monkeypatch.delenv("DEEPFAKE_THRESHOLD", raising=False)
    stored = load_head(HEAD_PATHS[kind])[1]["threshold"]
    assert create_detector(kind).threshold == pytest.approx(stored)
    monkeypatch.setenv("DEEPFAKE_THRESHOLD", "0.5")
    assert create_detector(kind).threshold == 0.5


@pytest.mark.parametrize(("name", "value"), [("DEEPFAKE_MODEL", "resnet"), ("DEEPFAKE_FRAMES", "8")])
def test_invalid_head_config_is_rejected(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=r"DEEPFAKE_MODEL|DEEPFAKE_FRAMES"):
        create_detector("mlp" if name == "DEEPFAKE_FRAMES" else None)


@pytest.mark.skipif(not SAMPLE_VIDEO.is_file(), reason=f"local test video missing: {SAMPLE_VIDEO}")
@pytest.mark.parametrize("kind", [
    "baseline", pytest.param("mlp", marks=needs_head("mlp")), pytest.param("temporal", marks=needs_head("temporal")),
])
def test_each_mode_runs_on_fixture_video(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str) -> None:
    monkeypatch.setenv("DEEPFAKE_MODEL", kind)
    detector = create_detector()
    assert detector.load_error is None
    result = detector.predict(SAMPLE_VIDEO, artifact_dir=tmp_path)
    assert (result["prediction"] == "FAKE") == (result["fake_probability"] >= detector.threshold)
    assert result["fake_probability"] == pytest.approx(detector.score_video(SAMPLE_VIDEO), abs=1e-5)
    # Frame scores and Grad-CAM always come from the backbone's own classifier.
    baseline_scores = VideoDetector().score_frames(SAMPLE_VIDEO)
    assert [item["fake_probability"] for item in result["frame_scores"]] == pytest.approx(baseline_scores, abs=1e-5)
    assert all((tmp_path / f"heatmap_{item['frame_id']}.jpg").is_file() for item in result["frame_scores"])
    assert detector.frame_threshold == (detector.threshold if kind == "baseline" else DEFAULT_THRESHOLD)

from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from app.services.video_detector import VideoDetector, VideoInferenceError


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_VIDEO = ROOT / "datasets/raw/test/00272.mp4"


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
    result = VideoDetector().predict(SAMPLE_VIDEO)
    assert result["prediction"] in {"REAL", "FAKE"}
    assert 0 <= result["confidence"] <= 1
    assert 0 <= result["fake_probability"] <= 1
    assert result["frames_analyzed"] == 2


def test_video_without_detectable_face_fails_cleanly(tmp_path: Path) -> None:
    path = tmp_path / "blank.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 5, (64, 64))
    for _ in range(2):
        writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
    writer.release()
    with pytest.raises(VideoInferenceError, match="No detectable face"):
        VideoDetector().predict(path)
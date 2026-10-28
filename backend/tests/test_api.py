from fastapi.testclient import TestClient
from pathlib import Path

from app import main
from app.main import app


client = TestClient(app)
ROOT = Path(__file__).resolve().parents[2]


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["inference_mode"] == main.video_detector.inference_mode
    assert body["model"] == main.video_detector.signal_name
    assert body["decision_threshold"] == main.video_detector.threshold


def test_cors_allows_local_frontend() -> None:
    response = client.options(
        "/api/v1/analyze",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_upload_completes_and_returns_evidence() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("sample.jpg", b"\xff\xd8\xff\xe0sample-jpeg-payload", "image/jpeg")},
    )
    assert response.status_code == 202
    analysis_id = response.json()["analysis_id"]

    result = client.get(f"/api/v1/analyze/{analysis_id}")
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "completed"
    assert body["sha256"]
    assert body["result"]["signals"]

    evidence = client.get(f"/api/v1/analyze/{analysis_id}/evidence")
    assert evidence.status_code == 200
    assert evidence.json()[0]["name"] == "Visual model"


def test_analysis_history_returns_uploaded_records() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("history.jpg", b"\xff\xd8\xff\xe0history-jpeg-payload", "image/jpeg")},
    )
    assert response.status_code == 202

    history = client.get("/api/v1/analyze")
    assert history.status_code == 200
    assert history.json()[0]["analysis_id"] == response.json()["analysis_id"]


def test_rejects_unsupported_extension() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("payload.exe", b"not-media", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_rejects_mismatched_file_content() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("sample.jpg", b"plain text", "image/jpeg")},
    )
    assert response.status_code == 415


def test_real_video_upload_returns_model_result() -> None:
    video_path = ROOT / "datasets/raw/test/00272.mp4"
    with video_path.open("rb") as video:
        response = client.post(
            "/api/v1/analyze",
            files={"file": (video_path.name, video, "video/mp4")},
        )
    assert response.status_code == 202
    result = client.get(f"/api/v1/analyze/{response.json()['analysis_id']}")
    body = result.json()
    assert body["status"] == "completed"
    assert 1 <= body["result"]["frames_analyzed"] <= main.video_detector.frames
    assert body["result"]["decision_threshold"] == main.video_detector.threshold
    assert body["result"]["frame_threshold"] == main.video_detector.frame_threshold
    assert body["result"]["model_name"] == main.video_detector.signal_name
    assert len(body["result"]["frame_scores"]) == body["result"]["frames_analyzed"]
    assert body["result"]["fake_probability"] is not None
    assert body["result"]["real_probability"] is not None


def test_video_frame_artifacts_are_served() -> None:
    video_path = ROOT / "datasets/raw/test/00272.mp4"
    with video_path.open("rb") as video:
        response = client.post(
            "/api/v1/analyze",
            files={"file": (video_path.name, video, "video/mp4")},
        )
    analysis_id = response.json()["analysis_id"]
    frame = client.get(f"/api/v1/analyze/{analysis_id}").json()["result"]["frame_scores"][0]
    for url in (frame["thumbnail_url"], frame["heatmap_url"]):
        image = client.get(url)
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/jpeg"
        assert image.content[:3] == b"\xff\xd8\xff"
    assert client.get(f"/api/v1/analyze/{analysis_id}/frames/999999/frame").status_code == 404
    assert client.get("/api/v1/analyze/DF-missing/frames/0/frame").status_code == 404


def test_unexpected_detector_error_marks_failed_and_deletes_upload(monkeypatch) -> None:
    def explode(*_args, **_kwargs):
        raise RuntimeError("simulated detector crash")

    monkeypatch.setattr(main.analysis_service.video_detector, "predict", explode)
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("crash.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64, "video/mp4")},
    )
    assert response.status_code == 202
    analysis_id = response.json()["analysis_id"]

    body = client.get(f"/api/v1/analyze/{analysis_id}").json()
    assert body["status"] == "failed"
    assert "RuntimeError" in body["error"]
    assert not (main.UPLOAD_ROOT / f"{analysis_id}.mp4").exists()

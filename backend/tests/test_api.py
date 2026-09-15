from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app


client = TestClient(app)
ROOT = Path(__file__).resolve().parents[2]


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["inference_mode"] == "efficientnet_b0_video"


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
    assert body["result"]["frames_analyzed"] == 2
    assert body["result"]["fake_probability"] is not None
    assert body["result"]["real_probability"] is not None

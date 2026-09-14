from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["inference_mode"] == "placeholder"


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

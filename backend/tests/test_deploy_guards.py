"""Deployment-mode behaviour: sync analysis, rate limit, busy response, private history, retention, CORS."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app
from app.services.guards import AnalysisSlots, RateLimiter

client = TestClient(app)
JPEG = b"\xff\xd8\xff\xe0guard-test-payload"


def upload(name: str = "guard.jpg", payload: bytes = JPEG, **kwargs):
    return client.post("/api/v1/analyze", files={"file": (name, payload, "image/jpeg")}, **kwargs)


@pytest.fixture(autouse=True)
def fresh_guards(monkeypatch):
    monkeypatch.setattr(main, "rate_limiter", RateLimiter(0))
    monkeypatch.setattr(main, "analysis_slots", AnalysisSlots(1))


def test_sync_mode_finishes_inside_the_request(monkeypatch) -> None:
    monkeypatch.setattr(main, "SYNC_ANALYSIS", True)
    response = upload()
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    record = client.get(f"/api/v1/analyze/{response.json()['analysis_id']}").json()
    assert record["status"] == "completed"
    assert not list(main.UPLOAD_ROOT.glob(f"{record['analysis_id']}*"))
    assert main.analysis_slots.try_acquire(), "slot must be released after a sync analysis"


def test_async_mode_still_returns_202(monkeypatch) -> None:
    monkeypatch.setattr(main, "SYNC_ANALYSIS", False)
    assert upload().status_code == 202
    assert main.analysis_slots.try_acquire(), "slot must be released after the background task"


def test_rate_limit_returns_429_with_retry_after(monkeypatch) -> None:
    monkeypatch.setattr(main, "rate_limiter", RateLimiter(2))
    assert upload().status_code in {200, 202}
    assert upload().status_code in {200, 202}
    limited = upload()
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0


def test_rejected_uploads_do_not_count_towards_the_limit(monkeypatch) -> None:
    monkeypatch.setattr(main, "rate_limiter", RateLimiter(1))
    assert upload(payload=b"not a jpeg").status_code == 415
    assert upload().status_code in {200, 202}


def test_rate_limit_keys_on_last_forwarded_hop(monkeypatch) -> None:
    monkeypatch.setattr(main, "rate_limiter", RateLimiter(1))
    monkeypatch.setattr(main, "TRUST_X_FORWARDED_FOR", True)
    assert upload(headers={"X-Forwarded-For": "1.1.1.1, 203.0.113.7"}).status_code in {200, 202}
    # A spoofed first hop does not reset the limit for the same real client.
    assert upload(headers={"X-Forwarded-For": "9.9.9.9, 203.0.113.7"}).status_code == 429
    assert upload(headers={"X-Forwarded-For": "198.51.100.2"}).status_code in {200, 202}


def test_busy_server_returns_503_and_keeps_no_upload() -> None:
    assert main.analysis_slots.try_acquire()
    try:
        before = set(main.UPLOAD_ROOT.iterdir())
        busy = upload()
        assert busy.status_code == 503
        assert busy.headers["retry-after"] == str(main.BUSY_RETRY_AFTER_SECONDS)
        assert set(main.UPLOAD_ROOT.iterdir()) == before
    finally:
        main.analysis_slots.release()


def test_slot_is_released_after_a_rejected_upload() -> None:
    assert upload(name="bad.exe").status_code == 415
    assert main.analysis_slots.try_acquire()
    main.analysis_slots.release()


def test_oversized_upload_returns_413(monkeypatch) -> None:
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 10)
    response = upload()
    assert response.status_code == 413
    assert "MB limit" in response.json()["detail"]


def test_history_requires_admin_token_when_protected(monkeypatch) -> None:
    monkeypatch.setattr(main, "PROTECT_LIST", True)
    monkeypatch.setattr(main, "ADMIN_TOKEN", "s3cret")
    assert client.get("/api/v1/analyze").status_code == 401
    assert client.get("/api/v1/analyze", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/v1/analyze", headers={"Authorization": "Bearer s3cret"}).status_code == 200
    # A single analysis stays readable by its ID.
    analysis_id = upload().json()["analysis_id"]
    assert client.get(f"/api/v1/analyze/{analysis_id}").status_code == 200


def test_protected_history_without_token_is_closed(monkeypatch) -> None:
    monkeypatch.setattr(main, "PROTECT_LIST", True)
    monkeypatch.setattr(main, "ADMIN_TOKEN", "")
    assert client.get("/api/v1/analyze", headers={"Authorization": "Bearer "}).status_code == 401


def test_retention_removes_old_records_and_artifacts() -> None:
    analysis_id = upload().json()["analysis_id"]
    artifact_dir = main.ARTIFACT_ROOT / analysis_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "frame_0.jpg").write_bytes(b"x")
    record = main.repository.get(analysis_id)
    main.repository.update(record.model_copy(update={"created_at": datetime.now(UTC) - timedelta(days=1)}))

    main.enforce_retention(force=True)
    assert main.repository.get(analysis_id) is None
    assert not artifact_dir.exists()
    assert client.get(f"/api/v1/analyze/{analysis_id}").status_code == 404


def test_retention_keeps_processing_records() -> None:
    analysis_id = upload().json()["analysis_id"]
    record = main.repository.get(analysis_id)
    main.repository.update(
        record.model_copy(update={"status": "processing", "created_at": datetime.now(UTC) - timedelta(days=1)})
    )
    main.enforce_retention(force=True)
    assert main.repository.get(analysis_id) is not None


def test_cors_origins_come_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://shield.example.workers.dev/, https://other.example ")
    assert main._env_list("ALLOWED_ORIGINS", []) == ["https://shield.example.workers.dev", "https://other.example"]
    monkeypatch.delenv("ALLOWED_ORIGINS")
    assert main._env_list("ALLOWED_ORIGINS", ["fallback"]) == ["fallback"]


def test_cors_exposes_retry_after() -> None:
    response = client.post(
        "/api/v1/analyze",
        headers={"Origin": "http://localhost:5173"},
        files={"file": ("x.exe", b"x", "application/octet-stream")},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "retry-after" in response.headers["access-control-expose-headers"].lower()


def test_health_reports_deploy_limits() -> None:
    body = client.get("/health").json()
    assert body["max_upload_bytes"] == main.MAX_UPLOAD_BYTES
    assert body["retention_seconds"] == main.RETENTION_SECONDS
    assert body["sync_analysis"] == main.SYNC_ANALYSIS

import logging
import mimetypes
import os
import secrets
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import gettempdir
from threading import Lock
from typing import Literal
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.schemas import (
    AnalysisCreateResponse,
    AnalysisRecord,
    AnalysisStatus,
    EvidenceSignal,
    HealthResponse,
    MediaType,
)
from app.services.analysis import AnalysisService, sha256_file
from app.services.guards import AnalysisSlots, RateLimiter
from app.services.repository import AnalysisRepository
from app.services.video_detector import create_detector

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"} if value else default


def _env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name, "").strip()
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()] if value else default


# Cloud Run rejects HTTP/1 request bodies over 32 MiB (33,554,432 bytes) before they reach the app.
# 32 MB (decimal) leaves ~1.5 MB for the multipart envelope.
MAX_UPLOAD_BYTES = _env_int("DEEPFAKE_SHIELD_MAX_UPLOAD_BYTES", 32_000_000)
# Finish the analysis inside the POST request. Cloud Run throttles CPU once a response is sent,
# so a background task there would crawl.
SYNC_ANALYSIS = _env_bool("SYNC_ANALYSIS", False)
# Accepted analyses per client per hour; 0 disables the limit.
RATE_LIMIT_PER_HOUR = _env_int("RATE_LIMIT_PER_HOUR", 0)
# Behind Cloud Run's front end the TCP peer is Google's proxy; the client is the last X-Forwarded-For hop.
TRUST_X_FORWARDED_FOR = _env_bool("TRUST_X_FORWARDED_FOR", False)
MAX_CONCURRENT_ANALYSES = _env_int("MAX_CONCURRENT_ANALYSES", 1)
BUSY_RETRY_AFTER_SECONDS = 15
# Finished records and their frame images are deleted after this long (and beyond MAX_RECORDS).
RETENTION_SECONDS = _env_int("RETENTION_SECONDS", 3600)
MAX_RECORDS = _env_int("MAX_RECORDS", 200)
# The history endpoint lists every visitor's uploads. With PROTECT_LIST it needs ADMIN_TOKEN as a
# bearer token; with PROTECT_LIST and no token it is closed to everyone.
PROTECT_LIST = _env_bool("PROTECT_LIST", False)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()
LOCAL_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
]
ALLOWED_ORIGINS = _env_list("ALLOWED_ORIGINS", LOCAL_ORIGINS)

UPLOAD_ROOT = Path(os.getenv("DEEPFAKE_SHIELD_UPLOAD_ROOT") or Path(gettempdir()) / "deepfake-shield-uploads")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
# Records live in memory, so artifacts from a previous process can never be requested again.
# (Safe because the service runs exactly one worker process.)
ARTIFACT_ROOT = Path(gettempdir()) / "deepfake-shield-artifacts"
shutil.rmtree(ARTIFACT_ROOT, ignore_errors=True)
ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_MEDIA: dict[MediaType, set[str]] = {
    MediaType.IMAGE: {".jpg", ".jpeg", ".png", ".webp"},
    MediaType.VIDEO: {".mp4", ".mov", ".avi", ".webm"},
    MediaType.AUDIO: {".wav", ".mp3", ".flac", ".m4a"},
}

MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
    ".wav": (b"RIFF",),
    ".mp3": (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"),
    ".flac": (b"fLaC",),
    ".mp4": (b"ftyp",),
    ".mov": (b"ftyp",),
    ".avi": (b"RIFF",),
    ".webm": (b"\x1a\x45\xdf\xa3",),
    ".m4a": (b"ftyp",),
}

repository = AnalysisRepository()
# DEEPFAKE_MODEL picks the head: mlp (default), temporal or baseline.
video_detector = create_detector()
analysis_service = AnalysisService(repository, video_detector, artifact_root=ARTIFACT_ROOT)
rate_limiter = RateLimiter(RATE_LIMIT_PER_HOUR)
analysis_slots = AnalysisSlots(MAX_CONCURRENT_ANALYSES)
app = FastAPI(title="DeepFake Shield API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    # The frontend reads Retry-After to tell the user when to try again.
    expose_headers=["Retry-After"],
)
_last_cleanup = 0.0
_cleanup_lock = Lock()


def enforce_retention(force: bool = False) -> None:
    """Delete expired records and their frame images; runs at most once a minute unless forced."""
    global _last_cleanup
    now = time.monotonic()
    with _cleanup_lock:
        if not force and now - _last_cleanup < 60:
            return
        _last_cleanup = now
    cutoff = datetime.now(UTC) - timedelta(seconds=RETENTION_SECONDS)
    for analysis_id in repository.prune(created_before=cutoff, keep_latest=MAX_RECORDS):
        shutil.rmtree(ARTIFACT_ROOT / analysis_id, ignore_errors=True)


def client_key(request: Request) -> str:
    if TRUST_X_FORWARDED_FOR:
        forwarded = request.headers.get("x-forwarded-for", "")
        # Clients can prepend anything; the proxy appends the address it saw, so take the last hop.
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if hops:
            return hops[-1]
    return request.client.host if request.client else "unknown"


def require_admin(request: Request) -> None:
    if not PROTECT_LIST:
        return
    supplied = request.headers.get("authorization", "")
    expected = f"Bearer {ADMIN_TOKEN}"
    if not ADMIN_TOKEN or not secrets.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The analysis history is private. Open analyses by their ID instead.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def classify_media(filename: str) -> MediaType:
    suffix = Path(filename).suffix.lower()
    for media_type, extensions in ALLOWED_MEDIA.items():
        if suffix in extensions:
            return media_type
    raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported media format")


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    if not name or name in {".", ".."}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A valid filename is required")
    return name


def validate_signature(path: Path, filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    signatures = MAGIC_SIGNATURES[suffix]
    header = path.read_bytes()[:16]
    valid = any(signature in header[:12] for signature in signatures)
    if suffix in {".webp", ".wav", ".avi"} and header[:4] == b"RIFF":
        expected_marker = {".webp": b"WEBP", ".wav": b"WAVE", ".avi": b"AVI "}[suffix]
        valid = header[8:12] == expected_marker
    if not valid:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="File content does not match its extension")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok" if video_detector.load_error is None else "degraded",
        service="deepfake-shield-api",
        inference_mode=video_detector.inference_mode,
        model=video_detector.signal_name,
        decision_threshold=video_detector.threshold,
        max_upload_bytes=MAX_UPLOAD_BYTES,
        retention_seconds=RETENTION_SECONDS,
        sync_analysis=SYNC_ANALYSIS,
    )


@app.post(
    "/api/v1/analyze",
    response_model=AnalysisCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={200: {"description": "Analysis finished inside the request (SYNC_ANALYSIS)"}},
)
def create_analysis(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> AnalysisCreateResponse:
    enforce_retention()
    client = client_key(request)
    retry_after = rate_limiter.retry_after(client)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Upload limit reached ({RATE_LIMIT_PER_HOUR} analyses per hour). Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    if not analysis_slots.try_acquire():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The server is busy with another analysis. Try again in a few seconds.",
            headers={"Retry-After": str(BUSY_RETRY_AFTER_SECONDS)},
        )
    handed_off = False
    try:
        analysis_id, media_path = _accept_upload(file)
        rate_limiter.record(client)
        if SYNC_ANALYSIS:
            analysis_service.run(analysis_id, media_path)
            record = get_record_or_404(analysis_id)
            response.status_code = status.HTTP_200_OK
            return AnalysisCreateResponse(analysis_id=analysis_id, status=record.status)
        background_tasks.add_task(_run_and_release, analysis_id, media_path)
        handed_off = True
        return AnalysisCreateResponse(analysis_id=analysis_id, status=AnalysisStatus.PROCESSING)
    finally:
        if not handed_off:
            analysis_slots.release()


def _run_and_release(analysis_id: str, media_path: Path) -> None:
    try:
        analysis_service.run(analysis_id, media_path)
    finally:
        analysis_slots.release()


def _accept_upload(file: UploadFile) -> tuple[str, Path]:
    """Store and validate the upload and create its PROCESSING record."""
    filename = safe_filename(file.filename or "")
    media_type = classify_media(filename)
    analysis_id = f"DF-{datetime.now(UTC):%Y%m%d}-{uuid4().hex[:8].upper()}"
    media_path = UPLOAD_ROOT / f"{analysis_id}{Path(filename).suffix.lower()}"

    total_bytes = 0
    try:
        with media_path.open("wb") as destination:
            while chunk := file.file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {MAX_UPLOAD_BYTES / 1_000_000:g} MB limit",
                    )
                destination.write(chunk)
    except HTTPException:
        media_path.unlink(missing_ok=True)
        raise
    except OSError as error:
        media_path.unlink(missing_ok=True)
        logger.exception("Unable to store upload")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to store upload") from error

    if total_bytes == 0:
        media_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    try:
        validate_signature(media_path, filename)
    except HTTPException:
        media_path.unlink(missing_ok=True)
        raise

    record = AnalysisRecord(
        analysis_id=analysis_id,
        filename=filename,
        media_type=media_type,
        content_type=file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        size_bytes=total_bytes,
        sha256=sha256_file(media_path),
        status=AnalysisStatus.PROCESSING,
        created_at=datetime.now(UTC),
    )
    repository.create(record)
    return analysis_id, media_path


def get_record_or_404(analysis_id: str) -> AnalysisRecord:
    enforce_retention()
    record = repository.get(analysis_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return record


@app.get("/api/v1/analyze/{analysis_id}", response_model=AnalysisRecord)
def get_analysis(analysis_id: str) -> AnalysisRecord:
    return get_record_or_404(analysis_id)


@app.get("/api/v1/analyze", response_model=list[AnalysisRecord], dependencies=[Depends(require_admin)])
def list_analyses() -> list[AnalysisRecord]:
    enforce_retention()
    return repository.list()


@app.get("/api/v1/analyze/{analysis_id}/evidence", response_model=list[EvidenceSignal])
def get_evidence(analysis_id: str) -> list[EvidenceSignal]:
    record = get_record_or_404(analysis_id)
    return record.result.signals if record.result else []


@app.get("/api/v1/analyze/{analysis_id}/report", response_model=AnalysisRecord)
def get_report(analysis_id: str) -> AnalysisRecord:
    return get_record_or_404(analysis_id)


@app.get("/api/v1/analyze/{analysis_id}/frames/{frame_id}/{kind}")
def get_frame_artifact(analysis_id: str, frame_id: int, kind: Literal["frame", "heatmap"]) -> FileResponse:
    get_record_or_404(analysis_id)
    path = ARTIFACT_ROOT / analysis_id / f"{kind}_{frame_id}.jpg"
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame artifact not found")
    return FileResponse(path, media_type="image/jpeg")

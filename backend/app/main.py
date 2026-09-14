import mimetypes
import secrets
import shutil
from datetime import UTC, datetime
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    AnalysisCreateResponse,
    AnalysisRecord,
    AnalysisStatus,
    EvidenceSignal,
    HealthResponse,
    MediaType,
)
from app.services.analysis import AnalysisService, sha256_file
from app.services.repository import AnalysisRepository

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
UPLOAD_ROOT = Path(gettempdir()) / "deepfake-shield-uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

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
analysis_service = AnalysisService(repository)
app = FastAPI(title="DeepFake Shield API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
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
    return HealthResponse(status="ok", service="deepfake-shield-api", inference_mode="placeholder")


@app.post("/api/v1/analyze", response_model=AnalysisCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_analysis(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> AnalysisCreateResponse:
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
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 100 MB limit")
                destination.write(chunk)
    except HTTPException:
        media_path.unlink(missing_ok=True)
        raise
    except OSError as error:
        media_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unable to store upload: {error}") from error

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
    background_tasks.add_task(_run_and_cleanup, analysis_id, media_path)
    return AnalysisCreateResponse(analysis_id=analysis_id, status=AnalysisStatus.PROCESSING)


def _run_and_cleanup(analysis_id: str, media_path: Path) -> None:
    analysis_service.run(analysis_id, media_path)
    media_path.unlink(missing_ok=True)


def get_record_or_404(analysis_id: str) -> AnalysisRecord:
    record = repository.get(analysis_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return record


@app.get("/api/v1/analyze/{analysis_id}", response_model=AnalysisRecord)
def get_analysis(analysis_id: str) -> AnalysisRecord:
    return get_record_or_404(analysis_id)


@app.get("/api/v1/analyze/{analysis_id}/evidence", response_model=list[EvidenceSignal])
def get_evidence(analysis_id: str) -> list[EvidenceSignal]:
    record = get_record_or_404(analysis_id)
    return record.result.signals if record.result else []


@app.get("/api/v1/analyze/{analysis_id}/report", response_model=AnalysisRecord)
def get_report(analysis_id: str) -> AnalysisRecord:
    return get_record_or_404(analysis_id)

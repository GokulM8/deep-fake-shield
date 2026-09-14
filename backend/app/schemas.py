from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AnalysisStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class Verdict(StrEnum):
    LIKELY_AUTHENTIC = "likely_authentic"
    LIKELY_MANIPULATED = "likely_manipulated"
    LIKELY_SYNTHETIC = "likely_synthetic"
    INCONCLUSIVE = "inconclusive"


class AnalysisCreateResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatus


class EvidenceSignal(BaseModel):
    name: str
    score: float = Field(ge=0, le=1)
    level: str
    explanation: str


class AnalysisResult(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    signals: list[EvidenceSignal]
    suspicious_regions: list[str] = Field(default_factory=list)
    suspicious_frames: list[float] = Field(default_factory=list)
    provenance: str


class AnalysisRecord(BaseModel):
    analysis_id: str
    filename: str
    media_type: MediaType
    content_type: str
    size_bytes: int
    sha256: str
    status: AnalysisStatus
    created_at: datetime
    completed_at: datetime | None = None
    result: AnalysisResult | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    inference_mode: str

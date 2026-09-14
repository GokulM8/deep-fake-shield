import hashlib
from datetime import UTC, datetime
from pathlib import Path

from app.schemas import (
    AnalysisRecord,
    AnalysisResult,
    AnalysisStatus,
    EvidenceSignal,
    MediaType,
    Verdict,
)
from app.services.repository import AnalysisRepository


class AnalysisService:
    """Coordinates analysis jobs while keeping inference replaceable."""

    def __init__(self, repository: AnalysisRepository) -> None:
        self.repository = repository

    def run(self, analysis_id: str, media_path: Path) -> None:
        record = self.repository.get(analysis_id)
        if record is None:
            return

        try:
            payload = media_path.read_bytes()
            result = self._placeholder_result(record.media_type, payload)
            completed = record.model_copy(
                update={
                    "status": AnalysisStatus.COMPLETED,
                    "completed_at": datetime.now(UTC),
                    "result": result,
                }
            )
            self.repository.update(completed)
        except OSError as error:
            failed = record.model_copy(
                update={
                    "status": AnalysisStatus.FAILED,
                    "completed_at": datetime.now(UTC),
                    "error": f"Unable to read uploaded media: {error}",
                }
            )
            self.repository.update(failed)

    @staticmethod
    def _placeholder_result(media_type: MediaType, payload: bytes) -> AnalysisResult:
        """Return deterministic scaffolding until trained models are connected."""
        digest = hashlib.sha256(payload).digest()
        visual_score = round(0.55 + (digest[0] / 255) * 0.35, 3)
        forensic_score = round(0.25 + (digest[1] / 255) * 0.45, 3)
        temporal_score = round(0.2 + (digest[2] / 255) * 0.5, 3)
        confidence = round((visual_score * 0.55) + (forensic_score * 0.25) + (temporal_score * 0.2), 3)
        verdict = Verdict.LIKELY_MANIPULATED if confidence >= 0.7 else Verdict.INCONCLUSIVE

        signals = [
            EvidenceSignal(
                name="Visual model",
                score=visual_score,
                level="high" if visual_score >= 0.7 else "medium",
                explanation="Placeholder signal; connect the trained image or frame model here.",
            ),
            EvidenceSignal(
                name="Forensic artifacts",
                score=forensic_score,
                level="medium",
                explanation="Placeholder signal for compression, texture, and boundary analysis.",
            ),
        ]
        if media_type == MediaType.VIDEO:
            signals.append(
                EvidenceSignal(
                    name="Temporal consistency",
                    score=temporal_score,
                    level="medium",
                    explanation="Placeholder signal for frame-to-frame consistency analysis.",
                )
            )
        if media_type == MediaType.AUDIO:
            signals[0] = signals[0].model_copy(
                update={
                    "name": "Synthetic speech model",
                    "explanation": "Placeholder signal for spectral and prosodic analysis.",
                }
            )

        return AnalysisResult(
            verdict=verdict,
            confidence=confidence,
            signals=signals,
            suspicious_regions=["face boundary"] if media_type == MediaType.IMAGE else [],
            suspicious_frames=[3.0, 4.0, 5.0] if media_type == MediaType.VIDEO else [],
            provenance="unknown",
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as media_file:
        for chunk in iter(lambda: media_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

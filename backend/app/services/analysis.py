import hashlib
import logging
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
from app.services.video_detector import VideoDetector, VideoInferenceError

logger = logging.getLogger(__name__)


class AnalysisService:
    """Coordinates analysis jobs while keeping inference replaceable."""

    def __init__(
        self,
        repository: AnalysisRepository,
        video_detector: VideoDetector,
        artifact_root: Path | None = None,
    ) -> None:
        self.repository = repository
        self.video_detector = video_detector
        self.artifact_root = artifact_root

    def run(self, analysis_id: str, media_path: Path) -> None:
        """Analyze the upload, always leaving the record COMPLETED or FAILED and the upload deleted."""
        try:
            self._run(analysis_id, media_path)
        finally:
            media_path.unlink(missing_ok=True)

    def _run(self, analysis_id: str, media_path: Path) -> None:
        record = self.repository.get(analysis_id)
        if record is None:
            return

        try:
            if record.media_type == MediaType.VIDEO:
                result = self._video_result(analysis_id, media_path)
            else:
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
        except (OSError, VideoInferenceError) as error:
            self._fail(record, f"Unable to read uploaded media: {error}")
        except Exception as error:
            logger.exception("Analysis %s failed unexpectedly", analysis_id)
            self._fail(record, f"Analysis failed due to an internal error ({type(error).__name__}). Please try again.")

    def _fail(self, record: AnalysisRecord, message: str) -> None:
        failed = record.model_copy(
            update={
                "status": AnalysisStatus.FAILED,
                "completed_at": datetime.now(UTC),
                "error": message,
            }
        )
        self.repository.update(failed)

    def _video_result(self, analysis_id: str, media_path: Path) -> AnalysisResult:
        artifact_dir = self.artifact_root / analysis_id if self.artifact_root else None
        prediction = self.video_detector.predict(media_path, artifact_dir=artifact_dir)
        if artifact_dir is not None:
            for item in prediction["frame_scores"]:
                base = f"/api/v1/analyze/{analysis_id}/frames/{item['frame_id']}"
                item["thumbnail_url"] = f"{base}/frame"
                item["heatmap_url"] = f"{base}/heatmap"
        fake_probability = prediction["fake_probability"]
        real_probability = prediction["real_probability"]
        is_fake = prediction["prediction"] == "FAKE"
        confidence = prediction["confidence"]
        return AnalysisResult(
            verdict=Verdict.LIKELY_MANIPULATED if is_fake else Verdict.LIKELY_AUTHENTIC,
            confidence=confidence,
            fake_probability=fake_probability,
            real_probability=real_probability,
            frames_analyzed=prediction["frames_analyzed"],
            frame_scores=prediction["frame_scores"],
            duration_seconds=prediction["duration_seconds"],
            frame_rate=prediction["frame_rate"],
            width=prediction["width"],
            height=prediction["height"],
            signals=[
                EvidenceSignal(
                    name=self.video_detector.signal_name,
                    score=fake_probability,
                    level="high" if is_fake else "low",
                    explanation=(
                        f"{self.video_detector.score_explanation}, "
                        f"flagged at {self.video_detector.threshold:g} or above; "
                        "this score is a model probability, not calibrated certainty."
                    ),
                ),
                EvidenceSignal(
                    name="Face frame coverage",
                    score=prediction["frames_analyzed"] / self.video_detector.frames,
                    # Coverage is a quality indicator, not a risk: full coverage is low risk.
                    level="low" if prediction["frames_analyzed"] == self.video_detector.frames else "medium",
                    explanation="Frames with no detectable face were skipped before inference.",
                ),
            ],
            suspicious_regions=["face boundary"] if is_fake else [],
            suspicious_frames=[
                float(item["timestamp"])
                for item in prediction["frame_scores"]
                if item["fake_probability"] >= self.video_detector.frame_threshold and item["timestamp"] is not None
            ],
            provenance=self.video_detector.provenance,
            model_name=self.video_detector.signal_name,
            decision_threshold=self.video_detector.threshold,
            frame_threshold=self.video_detector.frame_threshold,
        )

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

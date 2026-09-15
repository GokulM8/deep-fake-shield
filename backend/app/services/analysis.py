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
from app.services.video_detector import VideoDetector, VideoInferenceError


class AnalysisService:
    """Coordinates analysis jobs while keeping inference replaceable."""

    def __init__(self, repository: AnalysisRepository, video_detector: VideoDetector) -> None:
        self.repository = repository
        self.video_detector = video_detector

    def run(self, analysis_id: str, media_path: Path) -> None:
        record = self.repository.get(analysis_id)
        if record is None:
            return

        try:
            if record.media_type == MediaType.VIDEO:
                result = self._video_result(media_path)
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
            failed = record.model_copy(
                update={
                    "status": AnalysisStatus.FAILED,
                    "completed_at": datetime.now(UTC),
                    "error": f"Unable to read uploaded media: {error}",
                }
            )
            self.repository.update(failed)

    def _video_result(self, media_path: Path) -> AnalysisResult:
        prediction = self.video_detector.predict(media_path)
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
            signals=[
                EvidenceSignal(
                    name="EfficientNet-B0 video model",
                    score=fake_probability,
                    level="high" if is_fake else "low",
                    explanation=(
                        "Mean fake probability across detected faces in two sampled frames; "
                        "this score is a model probability, not calibrated certainty."
                    ),
                ),
                EvidenceSignal(
                    name="Face frame coverage",
                    score=prediction["frames_analyzed"] / self.video_detector.frames,
                    level="high" if prediction["frames_analyzed"] == self.video_detector.frames else "medium",
                    explanation="Frames with no detectable face were skipped before inference.",
                ),
            ],
            suspicious_regions=["face boundary"] if is_fake else [],
            suspicious_frames=[
                float(item["timestamp"])
                for item in prediction["frame_scores"]
                if item["fake_probability"] >= self.video_detector.threshold and item["timestamp"] is not None
            ],
            provenance="model checkpoint: deepfake_shield_video_v1.pt",
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

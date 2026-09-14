from threading import Lock

from app.schemas import AnalysisRecord


class AnalysisRepository:
    """Small in-memory repository for the local MVP.

    Replace this implementation with PostgreSQL persistence once the API contract
    is stable. The service layer does not depend on the storage mechanism.
    """

    def __init__(self) -> None:
        self._records: dict[str, AnalysisRecord] = {}
        self._lock = Lock()

    def create(self, record: AnalysisRecord) -> AnalysisRecord:
        with self._lock:
            self._records[record.analysis_id] = record
        return record

    def get(self, analysis_id: str) -> AnalysisRecord | None:
        with self._lock:
            return self._records.get(analysis_id)

    def update(self, record: AnalysisRecord) -> AnalysisRecord:
        with self._lock:
            self._records[record.analysis_id] = record
        return record

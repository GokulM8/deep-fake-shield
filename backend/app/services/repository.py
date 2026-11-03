from __future__ import annotations

from datetime import datetime
from threading import Lock

from app.schemas import AnalysisRecord, AnalysisStatus


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

    def list(self) -> list[AnalysisRecord]:
        with self._lock:
            return sorted(self._records.values(), key=lambda record: record.created_at, reverse=True)

    def update(self, record: AnalysisRecord) -> AnalysisRecord:
        with self._lock:
            # An update never resurrects a record that retention already removed.
            if record.analysis_id in self._records:
                self._records[record.analysis_id] = record
        return record

    def prune(self, created_before: datetime, keep_latest: int) -> list[str]:
        """Drop finished records created before ``created_before`` and all but the newest ``keep_latest``.

        Records still processing are never dropped. Returns the removed analysis IDs.
        """
        with self._lock:
            newest_first = sorted(self._records.values(), key=lambda record: record.created_at, reverse=True)
            removed = [
                record.analysis_id
                for index, record in enumerate(newest_first)
                if record.status != AnalysisStatus.PROCESSING
                and (record.created_at < created_before or index >= keep_latest)
            ]
            for analysis_id in removed:
                del self._records[analysis_id]
        return removed

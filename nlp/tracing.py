"""Privacy-safe persistence helpers for Falcon Mail NLP processing traces."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from database.auth_context import AuthenticatedUser
from database.base_repository import BaseComplaintRepository


logger = logging.getLogger("falcon_mail.pipeline_trace")


_PRIVATE_TRACE_KEYS = {
    "complaint_text",
    "dense_embedding",
    "description",
    "embedding",
    "matched_text",
    "original_text",
    "processed_text",
    "tokens",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_trace_value(value: Any, depth: int = 0) -> Any:
    """Keep traces concise and remove raw complaint text and dense vectors."""
    if depth > 4:
        return "[truncated]"
    if isinstance(value, dict):
        return {
            str(key): _sanitize_trace_value(item, depth + 1)
            for key, item in value.items()
            if str(key) not in _PRIVATE_TRACE_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_trace_value(item, depth + 1) for item in value[:20]]
    if isinstance(value, str):
        return value if len(value) <= 500 else value[:497] + "..."
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return str(value)[:500]


class NullPipelineTracer:
    """No-op tracer used for preview and non-persistent pipeline calls."""

    def start_stage(self, stage_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        pass

    def complete_stage(
        self,
        stage_name: str,
        result: Any = None,
        confidence: Optional[float] = None,
        model_or_rule: Optional[str] = None,
        evidence: Any = None,
    ) -> None:
        pass

    def fail_stage(
        self,
        stage_name: str,
        safe_error: str,
        diagnostic_code: Optional[str] = None,
    ) -> None:
        pass

    def complete_run(self, final_result: Dict[str, Any]) -> None:
        pass

    def fail_run(self, safe_error: str, diagnostic_code: Optional[str] = None) -> None:
        pass


class RepositoryPipelineTracer(NullPipelineTracer):
    """Persist genuine pipeline stage timing and concise operational output."""

    def __init__(
        self,
        repository: BaseComplaintRepository,
        run_id: str,
        actor: AuthenticatedUser,
    ) -> None:
        self.repository = repository
        self.run_id = run_id
        self.actor = actor
        self._started_at: Dict[str, str] = {}
        self._started_perf: Dict[str, float] = {}

    def _safe_stage_write(self, stage_name: str, stage_data: Dict[str, Any]) -> None:
        """Keep optional observability failures from changing ticket processing."""
        try:
            self.repository.update_processing_stage(
                self.run_id, stage_name, stage_data, self.actor
            )
        except Exception as error:
            logger.warning(
                "Could not persist NLP trace stage %s for run %s: %s",
                stage_name,
                self.run_id,
                error,
            )

    def _safe_finish_run(self, status: str, data: Dict[str, Any]) -> None:
        """Best-effort run finalization; complaint persistence remains authoritative."""
        try:
            self.repository.finish_processing_run(
                self.run_id, status, data, self.actor
            )
        except Exception as error:
            logger.warning(
                "Could not finalize NLP trace run %s as %s: %s",
                self.run_id,
                status,
                error,
            )

    def start_stage(self, stage_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        started_at = _utc_now()
        self._started_at[stage_name] = started_at
        self._started_perf[stage_name] = time.perf_counter()
        stage_data: Dict[str, Any] = {
            "status": "running",
            "started_at": started_at,
            "completed_at": None,
            "duration_ms": None,
        }
        if metadata:
            stage_data["metadata"] = _sanitize_trace_value(metadata)
        self._safe_stage_write(stage_name, stage_data)

    def complete_stage(
        self,
        stage_name: str,
        result: Any = None,
        confidence: Optional[float] = None,
        model_or_rule: Optional[str] = None,
        evidence: Any = None,
    ) -> None:
        completed_at = _utc_now()
        started_perf = self._started_perf.get(stage_name)
        duration_ms = (
            round((time.perf_counter() - started_perf) * 1000, 2)
            if started_perf is not None
            else None
        )
        self._safe_stage_write(
            stage_name,
            {
                "status": "completed",
                "started_at": self._started_at.get(stage_name),
                "completed_at": completed_at,
                "duration_ms": duration_ms,
                "result": _sanitize_trace_value(result),
                "confidence": confidence,
                "model_or_rule": model_or_rule,
                "evidence": _sanitize_trace_value(evidence),
            },
        )

    def fail_stage(
        self,
        stage_name: str,
        safe_error: str,
        diagnostic_code: Optional[str] = None,
    ) -> None:
        completed_at = _utc_now()
        started_perf = self._started_perf.get(stage_name)
        duration_ms = (
            round((time.perf_counter() - started_perf) * 1000, 2)
            if started_perf is not None
            else None
        )
        self._safe_stage_write(
            stage_name,
            {
                "status": "failed",
                "started_at": self._started_at.get(stage_name),
                "completed_at": completed_at,
                "duration_ms": duration_ms,
                "safe_error": safe_error[:500],
                "diagnostic_code": diagnostic_code,
            },
        )

    def complete_run(self, final_result: Dict[str, Any]) -> None:
        run_summary = {
            key: final_result.get(key)
            for key in (
                "complaint_id",
                "category",
                "urgency",
                "location",
                "department",
                "status",
            )
        }
        self._safe_finish_run(
            "completed",
            {
                "current_stage": "persistence",
                "final_result": _sanitize_trace_value(run_summary),
                "safe_error": None,
                "diagnostic_code": None,
            },
        )

    def fail_run(self, safe_error: str, diagnostic_code: Optional[str] = None) -> None:
        self._safe_finish_run(
            "needs_review",
            {
                "safe_error": safe_error[:500],
                "diagnostic_code": diagnostic_code,
            },
        )

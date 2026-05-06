from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from ..config.deps import PSYCOPG2_AVAILABLE
from ..config.models import CognitiveImmuneConfig
from ..state import AIOState

logger = logging.getLogger(__name__)


class ImmuneLearningEngine:
    """Persistent learned anomaly detection for the Cognitive Immune System.

    Stores historical immune snapshots in PostgreSQL, computes rolling
    statistical baselines, and derives a learned anomaly score from Z-scores.
    """

    _TABLE = "aio_immune_history"

    def __init__(self, config: CognitiveImmuneConfig, observability: Any) -> None:
        self.config = config
        self.obs = observability
        self._conn: Any = None
        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 package not installed; ImmuneLearningEngine will not persist data.")
            return
        if not config.learn_enable:
            return
        try:
            import psycopg2 as _pg

            self._conn = _pg.connect(config.learn_postgres_url)
            self._ensure_schema()
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Failed to connect to Postgres at %s: %s. ImmuneLearningEngine will not persist data.",
                config.learn_postgres_url,
                exc,
            )
            self._conn = None

    def _ensure_schema(self) -> None:
        if self._conn is None:
            return
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._TABLE} (
                    id SERIAL PRIMARY KEY,
                    timestamp DOUBLE PRECISION,
                    session_id TEXT,
                    failure_count INT,
                    safety_violation_count INT,
                    corrupted_memory_count INT,
                    retry_budget INT,
                    heuristic_anomaly_score DOUBLE PRECISION
                )
                """
            )
            self._conn.commit()

    def _extract_indicators(self, state: AIOState) -> Dict[str, Any]:
        failure_count = state.get("failure_count", 0) or 0
        safety_violations = state.get("safety_violations", []) or []
        safety_violation_count = len(safety_violations)
        wm = state.get("working_memory", []) or []
        corrupted_memory_count = sum(
            1 for m in wm if m is None or not isinstance(m, dict) or m.get("content") is None
        )
        retry_budget = state.get("retry_budget", 0) or 0
        heuristic_anomaly_score = state.get("anomaly_score", 0.0) or 0.0
        session_id = state.get("session_id", "")
        return {
            "timestamp": time.time(),
            "session_id": session_id,
            "failure_count": failure_count,
            "safety_violation_count": safety_violation_count,
            "corrupted_memory_count": corrupted_memory_count,
            "retry_budget": retry_budget,
            "heuristic_anomaly_score": heuristic_anomaly_score,
        }

    def record(self, state: AIOState) -> None:
        if self._conn is None:
            return
        try:
            indicators = self._extract_indicators(state)
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._TABLE}
                    (timestamp, session_id, failure_count, safety_violation_count,
                     corrupted_memory_count, retry_budget, heuristic_anomaly_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        indicators["timestamp"],
                        indicators["session_id"],
                        indicators["failure_count"],
                        indicators["safety_violation_count"],
                        indicators["corrupted_memory_count"],
                        indicators["retry_budget"],
                        indicators["heuristic_anomaly_score"],
                    ),
                )
                ttl = self.config.learn_record_ttl_seconds
                cutoff = time.time() - ttl
                cur.execute(
                    f"""
                    DELETE FROM {self._TABLE}
                    WHERE timestamp < %s
                    """,
                    (cutoff,),
                )
                self._conn.commit()
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to record immune snapshot: %s", exc)
            try:
                self._conn.rollback()
            except Exception:
                pass

    def _rolling_stats(self, column: str) -> tuple[float, float, int]:
        """Return (mean, std, count) for *column* over the rolling window."""
        if self._conn is None:
            return 0.0, 0.0, 0
        window = self.config.learn_rolling_window
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT AVG({column}), STDDEV({column}), COUNT({column})
                FROM (
                    SELECT {column}
                    FROM {self._TABLE}
                    ORDER BY id DESC
                    LIMIT %s
                ) AS sub
                """,
                (window,),
            )
            row = cur.fetchone()
            if row is None:
                return 0.0, 0.0, 0
            mean, std, count = row
        return float(mean or 0.0), float(std or 0.0), int(count or 0)

    def compute_anomaly_score(self, state: AIOState) -> float:
        if self._conn is None:
            return 0.0
        indicators = self._extract_indicators(state)
        metrics = [
            "failure_count",
            "safety_violation_count",
            "corrupted_memory_count",
        ]
        total_contribution = 0.0
        for metric in metrics:
            mean, std, count = self._rolling_stats(metric)
            if count < self.config.learn_min_samples:
                return 0.0
            current = float(indicators[metric])
            z = (current - mean) / (std + 1e-9)
            if z > self.config.learn_z_threshold:
                total_contribution += min(1.0, (z - self.config.learn_z_threshold) / 3.0)
        return round(min(1.0, total_contribution), 4)

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:  # pragma: no cover
                pass
            self._conn = None

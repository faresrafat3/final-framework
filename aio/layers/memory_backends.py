from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from ..config.deps import REDIS_AVAILABLE, PSYCOPG2_AVAILABLE, _check_pgvector_sql

logger = logging.getLogger(__name__)


class BaseMemoryBackend(ABC):
    """Abstract base for pluggable memory backends.

    Each backend exposes ``episodic``, ``long_term``, and ``keyword_index``
    as plain Python ``dict`` objects so that existing code and tests can
    continue to mutate them directly.  Persistent backends override
    :meth:`sync` to push local changes to the remote store.
    """

    def __init__(self) -> None:
        self.episodic: Dict[str, Dict[str, Any]] = {}
        self.long_term: Dict[str, Dict[str, Any]] = {}
        self.keyword_index: Dict[str, list] = {}

    @abstractmethod
    def sync(self) -> None:
        """Persist the current in-memory dicts to the backing store."""

    @abstractmethod
    def close(self) -> None:
        """Release any connections or resources held by the backend."""


class InMemoryBackend(BaseMemoryBackend):
    """Default no-op backend.  All state lives in process memory."""

    def sync(self) -> None:
        """No-op — data is already in memory."""
        pass

    def close(self) -> None:
        """No-op — no external resources are held."""
        pass


class RedisBackend(BaseMemoryBackend):
    """Persists memory dicts to Redis using hashes and sets.

    Falls back to a no-op if ``redis`` is unavailable or the server is
    unreachable on initialisation.

    Args:
        redis_url: Redis connection URL (e.g. ``redis://localhost:6379/0``).
    """

    _KEY_EPISODIC = "aio:memory:episodic"
    _KEY_LONG_TERM = "aio:memory:long_term"
    _KEY_KEYWORDS = "aio:memory:keywords"

    def __init__(self, redis_url: str) -> None:
        super().__init__()
        self._redis_url = redis_url
        self._client: Any = None
        if not REDIS_AVAILABLE:
            logger.warning("redis package not installed; RedisBackend will not persist data.")
            return
        try:
            import redis as _redis
            self._client = _redis.from_url(redis_url, decode_responses=True)
            self._client.ping()
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to connect to Redis at %s: %s. Data will not be persisted.", redis_url, exc)
            self._client = None
        self.load()

    def load(self) -> None:
        """Hydrate in-memory dicts from Redis hashes."""
        if self._client is None:
            return
        try:
            raw_epi = self._client.hgetall(self._KEY_EPISODIC)
            raw_lt = self._client.hgetall(self._KEY_LONG_TERM)
            raw_kw = self._client.hgetall(self._KEY_KEYWORDS)
            self.episodic = {k: json.loads(v) for k, v in raw_epi.items()}
            self.long_term = {k: json.loads(v) for k, v in raw_lt.items()}
            self.keyword_index = {k: json.loads(v) for k, v in raw_kw.items()}
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to load from Redis: %s", exc)

    def sync(self) -> None:
        """Atomically replace Redis hashes with the current in-memory dicts."""
        if self._client is None:
            return
        try:
            pipe = self._client.pipeline()
            pipe.delete(self._KEY_EPISODIC, self._KEY_LONG_TERM, self._KEY_KEYWORDS)
            if self.episodic:
                pipe.hset(self._KEY_EPISODIC, mapping={k: json.dumps(v, default=str) for k, v in self.episodic.items()})
            if self.long_term:
                pipe.hset(self._KEY_LONG_TERM, mapping={k: json.dumps(v, default=str) for k, v in self.long_term.items()})
            if self.keyword_index:
                pipe.hset(self._KEY_KEYWORDS, mapping={k: json.dumps(v, default=str) for k, v in self.keyword_index.items()})
            pipe.execute()
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to sync to Redis: %s", exc)

    def close(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # pragma: no cover
                pass
            self._client = None


class PostgresBackend(BaseMemoryBackend):
    """Persists memory dicts to PostgreSQL with optional pgvector ANN support.

    When ``pgvector_enable`` is *True* and the pgvector extension is
    installed in the target database, the backend stores embeddings in a
    native ``vector`` column and supports HNSW-based approximate nearest-
    neighbour search.  If pgvector is unavailable it gracefully degrades to
    a JSONB-only mode that preserves all existing behaviour.

    Args:
        postgres_url: PostgreSQL connection URL.
        vector_dimension: Dimensionality of embedding vectors (default 384).
        pgvector_enable: Whether to attempt pgvector schema and operations.
    """

    _TABLE_ENTRIES = "aio_memory_entries"
    _TABLE_KEYWORDS = "aio_memory_keywords"

    def __init__(
        self,
        postgres_url: str,
        vector_dimension: int = 384,
        pgvector_enable: bool = True,
    ) -> None:
        super().__init__()
        self._postgres_url = postgres_url
        self._vector_dimension = vector_dimension
        self._pgvector_enable = pgvector_enable
        self._conn: Any = None
        self._pgvector_active = False

        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 package not installed; PostgresBackend will not persist data.")
            return

        try:
            import psycopg2 as _pg
            self._conn = _pg.connect(postgres_url)
            self._pgvector_active = self._check_pgvector_available()
            if self._pgvector_enable and not self._pgvector_active:
                logger.warning(
                    "pgvector extension not available in Postgres at %s; "
                    "degrading to JSONB mode (no ANN, no vector column ops).",
                    postgres_url,
                )
            self._ensure_schema()
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Failed to connect to Postgres at %s: %s. Data will not be persisted.",
                postgres_url,
                exc,
            )
            self._conn = None
            self._pgvector_active = False

        self.load()

    # ------------------------------------------------------------------
    # Schema & pgvector probes
    # ------------------------------------------------------------------

    def _check_pgvector_available(self) -> bool:
        """Return *True* if the pgvector extension is installed in the DB."""
        if self._conn is None:
            return False
        return _check_pgvector_sql(self._conn)

    def _ensure_schema(self) -> None:
        """Create required tables and indexes if they do not exist."""
        if self._conn is None:
            return

        with self._conn.cursor() as cur:
            if self._pgvector_active:
                cur.execute("CREATE EXTENSION IF NOT EXISTS pgvector")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._TABLE_ENTRIES} (
                        entry_id TEXT PRIMARY KEY,
                        store_type TEXT NOT NULL,
                        role TEXT,
                        content TEXT NOT NULL,
                        embedding vector({self._vector_dimension}),
                        importance FLOAT DEFAULT 0.5,
                        turn INT DEFAULT 0,
                        timestamp FLOAT DEFAULT 0,
                        verification_passed BOOLEAN DEFAULT FALSE,
                        metadata JSONB DEFAULT '{{}}'
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_memory_embedding_hnsw
                    ON {self._TABLE_ENTRIES}
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                    """
                )
            else:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._TABLE_ENTRIES} (
                        entry_id TEXT PRIMARY KEY,
                        store_type TEXT NOT NULL,
                        payload JSONB NOT NULL
                    )
                    """
                )

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._TABLE_KEYWORDS} (
                    keyword TEXT PRIMARY KEY,
                    entry_ids TEXT[] NOT NULL
                )
                """
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Load / Sync
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Hydrate in-memory dicts from PostgreSQL rows."""
        if self._conn is None:
            return
        try:
            with self._conn.cursor() as cur:
                if self._pgvector_active:
                    cur.execute(
                        f"""
                        SELECT entry_id, store_type, role, content, embedding,
                               importance, turn, timestamp, verification_passed, metadata
                        FROM {self._TABLE_ENTRIES}
                        """
                    )
                    for row in cur.fetchall():
                        eid, store_type, role, content, embedding, importance, turn, ts, verified, meta = row
                        entry: Dict[str, Any] = {
                            "id": eid,
                            "role": role,
                            "content": content,
                            "embedding": embedding,
                            "importance": importance,
                            "turn": turn,
                            "timestamp": ts,
                            "verification_passed": verified,
                        }
                        if meta:
                            entry.update(meta)
                        if store_type == "episodic":
                            self.episodic[eid] = entry
                        else:
                            self.long_term[eid] = entry
                else:
                    cur.execute(
                        f"SELECT entry_id, store_type, payload FROM {self._TABLE_ENTRIES}"
                    )
                    for eid, store_type, payload in cur.fetchall():
                        entry = dict(payload)
                        if store_type == "episodic":
                            self.episodic[eid] = entry
                        else:
                            self.long_term[eid] = entry

                cur.execute(f"SELECT keyword, entry_ids FROM {self._TABLE_KEYWORDS}")
                for keyword, entry_ids in cur.fetchall():
                    self.keyword_index[keyword] = list(entry_ids)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to load from Postgres: %s", exc)

    def sync(self) -> None:
        """Truncate and repopulate the PostgreSQL tables from current dicts."""
        if self._conn is None:
            return
        try:
            with self._conn.cursor() as cur:
                cur.execute(f"DELETE FROM {self._TABLE_ENTRIES}")
                cur.execute(f"DELETE FROM {self._TABLE_KEYWORDS}")

                if self._pgvector_active:
                    for eid, entry in self.episodic.items():
                        cur.execute(
                            f"""
                            INSERT INTO {self._TABLE_ENTRIES}
                            (entry_id, store_type, role, content, embedding,
                             importance, turn, timestamp, verification_passed, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                eid,
                                "episodic",
                                entry.get("role"),
                                entry.get("content", ""),
                                entry.get("embedding"),
                                entry.get("importance", 0.5),
                                entry.get("turn", 0),
                                entry.get("timestamp", 0.0),
                                entry.get("verification_passed", False),
                                json.dumps({k: v for k, v in entry.items()
                                            if k not in {"id", "role", "content", "embedding",
                                                         "importance", "turn", "timestamp",
                                                         "verification_passed"}}, default=str),
                            ),
                        )
                    for eid, entry in self.long_term.items():
                        cur.execute(
                            f"""
                            INSERT INTO {self._TABLE_ENTRIES}
                            (entry_id, store_type, role, content, embedding,
                             importance, turn, timestamp, verification_passed, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                eid,
                                "long_term",
                                entry.get("role"),
                                entry.get("content", ""),
                                entry.get("embedding"),
                                entry.get("importance", 0.5),
                                entry.get("turn", 0),
                                entry.get("timestamp", 0.0),
                                entry.get("verification_passed", False),
                                json.dumps({k: v for k, v in entry.items()
                                            if k not in {"id", "role", "content", "embedding",
                                                         "importance", "turn", "timestamp",
                                                         "verification_passed"}}, default=str),
                            ),
                        )
                else:
                    for eid, entry in self.episodic.items():
                        cur.execute(
                            f"INSERT INTO {self._TABLE_ENTRIES} (entry_id, store_type, payload) VALUES (%s, %s, %s)",
                            (eid, "episodic", json.dumps(entry, default=str)),
                        )
                    for eid, entry in self.long_term.items():
                        cur.execute(
                            f"INSERT INTO {self._TABLE_ENTRIES} (entry_id, store_type, payload) VALUES (%s, %s, %s)",
                            (eid, "long_term", json.dumps(entry, default=str)),
                        )

                for keyword, eids in self.keyword_index.items():
                    cur.execute(
                        f"INSERT INTO {self._TABLE_KEYWORDS} (keyword, entry_ids) VALUES (%s, %s)",
                        (keyword, list(eids)),
                    )
                self._conn.commit()
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to sync to Postgres: %s", exc)

    # ------------------------------------------------------------------
    # Vector search
    # ------------------------------------------------------------------

    def vector_search(
        self,
        query_embedding: List[float],
        store_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Pure ANN search using pgvector cosine distance.

        Args:
            query_embedding: The query vector.
            store_type: Filter by ``'episodic'`` or ``'long_term'`` (optional).
            top_k: Number of nearest neighbours to return.

        Returns:
            List of ``(entry_id, score)`` tuples sorted by descending score.
            Score is ``1 - cosine_distance`` so that higher is better.
        """
        if self._conn is None or not self._pgvector_active:
            return []

        params: List[Any] = [query_embedding]
        where_clause = ""
        if store_type is not None:
            where_clause = "AND store_type = %s"
            params.append(store_type)

        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT entry_id, 1 - (embedding <=> %s::vector) AS score
                    FROM {self._TABLE_ENTRIES}
                    WHERE embedding IS NOT NULL {where_clause}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (*params, query_embedding, top_k),
                )
                return [(row[0], float(row[1])) for row in cur.fetchall()]
        except Exception as exc:  # pragma: no cover
            logger.warning("vector_search failed: %s", exc)
            return []

    def hybrid_search(
        self,
        query_embedding: List[float],
        keywords: List[str],
        store_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Hybrid retrieval combining vector similarity and keyword overlap.

        Scoring formula (at SQL level)::

            total_score = vector_score * 0.6 + keyword_score * 0.4

        where ``vector_score = 1 - cosine_distance`` and ``keyword_score``
        is the Jaccard-like fraction of query keywords present in the entry's
        content (lower-cased, word-boundary match).

        Args:
            query_embedding: The query vector.
            keywords: Query keywords extracted from the raw input.
            store_type: Filter by ``'episodic'`` or ``'long_term'`` (optional).
            top_k: Number of top results to return.

        Returns:
            List of ``(entry_id, total_score)`` tuples sorted by descending score.
        """
        if self._conn is None or not self._pgvector_active:
            return []

        params: List[Any] = [query_embedding]
        where_clause = ""
        if store_type is not None:
            where_clause = "AND store_type = %s"
            params.append(store_type)

        keyword_patterns = [f"% {kw.lower()} %" for kw in keywords if kw]
        if not keyword_patterns:
            # No keywords — fall back to pure vector search
            return self.vector_search(query_embedding, store_type=store_type, top_k=top_k)

        # Build a SQL expression that counts how many keywords match the content.
        keyword_conditions = " OR ".join(
            f"LOWER(content) LIKE %s" for _ in keyword_patterns
        )
        keyword_params = keyword_patterns[:]

        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT entry_id,
                           (1 - (embedding <=> %s::vector)) * 0.6
                           + (CASE WHEN ({keyword_conditions}) THEN 0.4 ELSE 0.0 END) AS score
                    FROM {self._TABLE_ENTRIES}
                    WHERE embedding IS NOT NULL {where_clause}
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (query_embedding, *keyword_params, *params[1:], top_k),
                )
                return [(row[0], float(row[1])) for row in cur.fetchall()]
        except Exception as exc:  # pragma: no cover
            logger.warning("hybrid_search failed: %s", exc)
            return []

    def close(self) -> None:
        """Close the PostgreSQL connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:  # pragma: no cover
                pass
            self._conn = None


class HybridBackend(BaseMemoryBackend):
    """Hybrid backend: Redis for hot/episodic data, Postgres for cold/long-term.

    Internally manages its own Redis and Postgres connections so that each
    partition is synced to the appropriate store without double-writing.

    Args:
        redis_url: Redis connection URL.
        postgres_url: PostgreSQL connection URL.
    """

    def __init__(self, redis_url: str, postgres_url: str) -> None:
        super().__init__()
        self._redis = RedisBackend(redis_url)
        self._postgres = PostgresBackend(postgres_url)
        # Start with whatever each backend loaded (Redis may have episodic,
        # Postgres may have long_term).  In the common case where one side is
        # empty the union is just the populated side.
        self.episodic = self._redis.episodic
        self.long_term = self._postgres.long_term
        self.keyword_index = self._redis.keyword_index

    def sync(self) -> None:
        """Push episodic/keywords to Redis and long_term to Postgres."""
        # Push episodic/keyword_index to Redis, long_term to Postgres.
        self._redis.episodic = self.episodic
        self._redis.keyword_index = self.keyword_index
        self._redis.sync()
        self._postgres.long_term = self.long_term
        self._postgres.sync()

    def close(self) -> None:
        """Close both underlying backends."""
        self._redis.close()
        self._postgres.close()

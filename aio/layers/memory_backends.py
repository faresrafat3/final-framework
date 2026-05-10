from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple

from ..config.deps import REDIS_AVAILABLE, PSYCOPG2_AVAILABLE, _check_pgvector_sql

logger = logging.getLogger(__name__)


def _vector_literal(values: Optional[List[float]]) -> Optional[str]:
    if not isinstance(values, list) or not values:
        return None
    try:
        return "[" + ",".join(f"{float(v):.12g}" for v in values) + "]"
    except Exception:
        return None


def _parse_embedding(raw: Any) -> Optional[List[float]]:
    if raw is None:
        return None
    if isinstance(raw, list):
        try:
            return [float(v) for v in raw]
        except Exception:
            return None
    if isinstance(raw, tuple):
        try:
            return [float(v) for v in raw]
        except Exception:
            return None
    if isinstance(raw, str):
        payload = raw.strip()
        if payload.startswith("[") and payload.endswith("]"):
            payload = payload[1:-1]
        if not payload:
            return None
        try:
            return [float(part.strip()) for part in payload.split(",") if part.strip()]
        except Exception:
            return None
    return None


def _safe_json_loads(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


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
            if self._pgvector_enable:
                self._pgvector_active = self._check_pgvector_available() or self._try_enable_pgvector_extension()
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

    def _rollback(self) -> None:
        if self._conn is not None and hasattr(self._conn, "rollback"):
            try:
                self._conn.rollback()
            except Exception:
                pass

    def _check_pgvector_available(self) -> bool:
        """Return *True* if the pgvector extension is installed in the DB."""
        if self._conn is None:
            return False
        return _check_pgvector_sql(self._conn)

    def _try_enable_pgvector_extension(self) -> bool:
        if self._conn is None:
            return False

        extension_names = ["pgvector", "vector"]
        for ext_name in extension_names:
            try:
                with self._conn.cursor() as cur:
                    cur.execute(f"CREATE EXTENSION IF NOT EXISTS {ext_name}")
                self._conn.commit()
                if self._check_pgvector_available():
                    return True
            except Exception:
                self._rollback()
        return False

    def _ensure_schema(self) -> None:
        """Create required tables and indexes if they do not exist."""
        if self._conn is None:
            return

        try:
            with self._conn.cursor() as cur:
                if self._pgvector_active:
                    try:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS pgvector")
                    except Exception:
                        self._rollback()
                        with self._conn.cursor() as ext_cur:
                            ext_cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
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
        except Exception as exc:  # pragma: no cover
            self._rollback()
            logger.warning("Failed to ensure Postgres memory schema: %s", exc)

    # ------------------------------------------------------------------
    # Load / Sync
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Hydrate in-memory dicts from PostgreSQL rows."""
        if self._conn is None:
            return
        self.episodic = {}
        self.long_term = {}
        self.keyword_index = {}
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
                            "embedding": _parse_embedding(embedding),
                            "importance": float(importance if importance is not None else 0.5),
                            "turn": int(turn if turn is not None else 0),
                            "timestamp": float(ts if ts is not None else 0.0),
                            "verification_passed": bool(verified),
                        }
                        meta_dict = _safe_json_loads(meta)
                        if meta_dict:
                            entry.update(meta_dict)
                        if store_type == "episodic":
                            self.episodic[eid] = entry
                        else:
                            self.long_term[eid] = entry
                else:
                    cur.execute(f"SELECT entry_id, store_type, payload FROM {self._TABLE_ENTRIES}")
                    for eid, store_type, payload in cur.fetchall():
                        entry = _safe_json_loads(payload)
                        if not entry:
                            continue
                        if store_type == "episodic":
                            self.episodic[eid] = entry
                        else:
                            self.long_term[eid] = entry

                cur.execute(f"SELECT keyword, entry_ids FROM {self._TABLE_KEYWORDS}")
                for keyword, entry_ids in cur.fetchall():
                    self.keyword_index[keyword] = list(dict.fromkeys(entry_ids or []))
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to load from Postgres: %s", exc)
            self._rollback()

    def _entry_metadata(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k: v
            for k, v in entry.items()
            if k
            not in {
                "id",
                "role",
                "content",
                "embedding",
                "importance",
                "turn",
                "timestamp",
                "verification_passed",
            }
        }

    def _upsert_pgvector_entries(
        self,
        cur: Any,
        entries: Dict[str, Dict[str, Any]],
        store_type: str,
    ) -> Set[str]:
        persisted_ids: Set[str] = set()
        for eid, entry in entries.items():
            embedding = _parse_embedding(entry.get("embedding"))
            embedding_lit = _vector_literal(embedding)
            if embedding_lit is not None and len(embedding or []) != self._vector_dimension:
                embedding_lit = None
            cur.execute(
                f"""
                INSERT INTO {self._TABLE_ENTRIES}
                (entry_id, store_type, role, content, embedding,
                 importance, turn, timestamp, verification_passed, metadata)
                VALUES (%s, %s, %s, %s, %s::vector, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (entry_id) DO UPDATE SET
                    store_type = EXCLUDED.store_type,
                    role = EXCLUDED.role,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    importance = EXCLUDED.importance,
                    turn = EXCLUDED.turn,
                    timestamp = EXCLUDED.timestamp,
                    verification_passed = EXCLUDED.verification_passed,
                    metadata = EXCLUDED.metadata
                """,
                (
                    eid,
                    store_type,
                    entry.get("role"),
                    entry.get("content", ""),
                    embedding_lit,
                    float(entry.get("importance", 0.5)),
                    int(entry.get("turn", 0)),
                    float(entry.get("timestamp", 0.0)),
                    bool(entry.get("verification_passed", False)),
                    json.dumps(self._entry_metadata(entry), default=str),
                ),
            )
            persisted_ids.add(eid)
        return persisted_ids

    def _upsert_jsonb_entries(
        self,
        cur: Any,
        entries: Dict[str, Dict[str, Any]],
        store_type: str,
    ) -> Set[str]:
        persisted_ids: Set[str] = set()
        for eid, entry in entries.items():
            cur.execute(
                f"""
                INSERT INTO {self._TABLE_ENTRIES} (entry_id, store_type, payload)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (entry_id) DO UPDATE SET
                    store_type = EXCLUDED.store_type,
                    payload = EXCLUDED.payload
                """,
                (eid, store_type, json.dumps(entry, default=str)),
            )
            persisted_ids.add(eid)
        return persisted_ids

    def sync(self) -> None:
        """Upsert changed rows and remove stale rows from PostgreSQL tables."""
        if self._conn is None:
            return

        try:
            with self._conn.cursor() as cur:
                persisted_ids: Set[str] = set()
                if self._pgvector_active:
                    persisted_ids.update(self._upsert_pgvector_entries(cur, self.episodic, "episodic"))
                    persisted_ids.update(self._upsert_pgvector_entries(cur, self.long_term, "long_term"))
                else:
                    persisted_ids.update(self._upsert_jsonb_entries(cur, self.episodic, "episodic"))
                    persisted_ids.update(self._upsert_jsonb_entries(cur, self.long_term, "long_term"))

                cur.execute(f"SELECT entry_id FROM {self._TABLE_ENTRIES}")
                existing_ids = {row[0] for row in cur.fetchall()}
                stale_ids = existing_ids - persisted_ids
                for stale_id in stale_ids:
                    cur.execute(f"DELETE FROM {self._TABLE_ENTRIES} WHERE entry_id = %s", (stale_id,))

                for keyword, eids in self.keyword_index.items():
                    uniq_ids = list(dict.fromkeys(eids))
                    cur.execute(
                        f"""
                        INSERT INTO {self._TABLE_KEYWORDS} (keyword, entry_ids)
                        VALUES (%s, %s)
                        ON CONFLICT (keyword) DO UPDATE SET entry_ids = EXCLUDED.entry_ids
                        """,
                        (keyword, uniq_ids),
                    )

                cur.execute(f"SELECT keyword FROM {self._TABLE_KEYWORDS}")
                existing_keywords = {row[0] for row in cur.fetchall()}
                stale_keywords = existing_keywords - set(self.keyword_index.keys())
                for keyword in stale_keywords:
                    cur.execute(f"DELETE FROM {self._TABLE_KEYWORDS} WHERE keyword = %s", (keyword,))

            self._conn.commit()
        except Exception as exc:  # pragma: no cover
            self._rollback()
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
        """Pure ANN search using pgvector cosine distance."""
        if self._conn is None or not self._pgvector_active:
            return []

        query_vector = _vector_literal(query_embedding)
        if query_vector is None:
            return []

        params: List[Any] = [query_vector]
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
                    (*params, query_vector, top_k),
                )
                return [(row[0], float(row[1])) for row in cur.fetchall()]
        except Exception as exc:  # pragma: no cover
            self._rollback()
            logger.warning("vector_search failed: %s", exc)
            return []

    def hybrid_search(
        self,
        query_embedding: List[float],
        keywords: List[str],
        store_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Hybrid retrieval combining vector similarity and keyword overlap."""
        if self._conn is None or not self._pgvector_active:
            return []

        cleaned_keywords = [kw.strip().lower() for kw in keywords if kw and kw.strip()]
        if not cleaned_keywords:
            return self.vector_search(query_embedding, store_type=store_type, top_k=top_k)

        query_vector = _vector_literal(query_embedding)
        if query_vector is None:
            return []

        where_clause = ""
        base_params: List[Any] = [query_vector]
        if store_type is not None:
            where_clause = "AND store_type = %s"
            base_params.append(store_type)

        keyword_expr = " + ".join(["CASE WHEN LOWER(content) LIKE %s THEN 1 ELSE 0 END" for _ in cleaned_keywords])
        keyword_patterns = [f"%{kw}%" for kw in cleaned_keywords]

        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT entry_id,
                           (1 - (embedding <=> %s::vector)) * 0.6
                           + ((({keyword_expr})::float / %s) * 0.4) AS score
                    FROM {self._TABLE_ENTRIES}
                    WHERE embedding IS NOT NULL {where_clause}
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (
                        base_params[0],
                        *keyword_patterns,
                        len(cleaned_keywords),
                        *base_params[1:],
                        top_k,
                    ),
                )
                return [(row[0], float(row[1])) for row in cur.fetchall()]
        except Exception as exc:  # pragma: no cover
            self._rollback()
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
        self._redis.episodic = self.episodic
        self._redis.keyword_index = self.keyword_index
        self._redis.sync()

        self._postgres.episodic = {}
        self._postgres.keyword_index = {}
        self._postgres.long_term = self.long_term
        self._postgres.sync()

    def close(self) -> None:
        """Close both underlying backends."""
        self._redis.close()
        self._postgres.close()

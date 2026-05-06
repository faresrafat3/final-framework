from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from ..config.deps import REDIS_AVAILABLE, PSYCOPG2_AVAILABLE

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
        pass

    def close(self) -> None:
        pass


class RedisBackend(BaseMemoryBackend):
    """Persists memory dicts to Redis using hashes and sets.

    Falls back to a no-op if ``redis`` is unavailable or the server is
    unreachable on initialisation.
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
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # pragma: no cover
                pass
            self._client = None


class PostgresBackend(BaseMemoryBackend):
    """Persists memory dicts to PostgreSQL using JSONB.

    Falls back to a no-op if ``psycopg2`` is unavailable or the server is
    unreachable on initialisation.
    """

    _TABLE_ENTRIES = "aio_memory_entries"
    _TABLE_KEYWORDS = "aio_memory_keywords"

    def __init__(self, postgres_url: str) -> None:
        super().__init__()
        self._postgres_url = postgres_url
        self._conn: Any = None
        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 package not installed; PostgresBackend will not persist data.")
            return
        try:
            import psycopg2 as _pg
            self._conn = _pg.connect(postgres_url)
            self._ensure_schema()
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to connect to Postgres at %s: %s. Data will not be persisted.", postgres_url, exc)
            self._conn = None
        self.load()

    def _ensure_schema(self) -> None:
        if self._conn is None:
            return
        with self._conn.cursor() as cur:
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
                    entry_ids JSONB NOT NULL
                )
                """
            )
            self._conn.commit()

    def load(self) -> None:
        if self._conn is None:
            return
        try:
            with self._conn.cursor() as cur:
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
        if self._conn is None:
            return
        try:
            with self._conn.cursor() as cur:
                cur.execute(f"DELETE FROM {self._TABLE_ENTRIES}")
                cur.execute(f"DELETE FROM {self._TABLE_KEYWORDS}")
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
                        (keyword, json.dumps(eids, default=str)),
                    )
                self._conn.commit()
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to sync to Postgres: %s", exc)

    def close(self) -> None:
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
        # Push episodic/keyword_index to Redis, long_term to Postgres.
        self._redis.episodic = self.episodic
        self._redis.keyword_index = self.keyword_index
        self._redis.sync()
        self._postgres.long_term = self.long_term
        self._postgres.sync()

    def close(self) -> None:
        self._redis.close()
        self._postgres.close()

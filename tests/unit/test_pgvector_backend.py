import pytest
from unittest.mock import MagicMock, patch

from aio.layers.memory_backends import PostgresBackend, InMemoryBackend


class FakeCursor:
    """Minimal mock cursor that records executed SQL and returns configurable rows."""

    def __init__(self, fetchall_return=None, fetchone_return=None):
        self._fetchall = fetchall_return or []
        self._fetchone = fetchone_return
        self.executed: list = []
        self.params: list = []

    def execute(self, sql, params=None):
        self.executed.append(sql)
        self.params.append(params)

    def fetchall(self):
        return self._fetchall

    def fetchone(self):
        return self._fetchone

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeConn:
    """Minimal mock connection that yields a FakeCursor."""

    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def close(self):
        pass


@pytest.fixture
def mocked_pgvector_backend():
    with patch("aio.layers.memory_backends.PSYCOPG2_AVAILABLE", True):
        with patch("aio.layers.memory_backends._check_pgvector_sql", return_value=True):
            with patch("psycopg2.connect") as mock_connect:
                cur = FakeCursor()
                conn = FakeConn(cur)
                mock_connect.return_value = conn
                backend = PostgresBackend(
                    "postgresql://localhost/aio",
                    vector_dimension=384,
                    pgvector_enable=True,
                )
                # Re-attach the cursor so tests can inspect SQL
                backend._test_cursor = cur  # type: ignore[attr-defined]
                yield backend


class TestPgvectorSchemaCreation:
    def test_pgvector_schema_creation(self, mocked_pgvector_backend):
        cur = mocked_pgvector_backend._test_cursor
        sql = " ".join(cur.executed)
        assert "CREATE EXTENSION IF NOT EXISTS pgvector" in sql
        assert "CREATE TABLE IF NOT EXISTS aio_memory_entries" in sql
        assert "embedding vector(384)" in sql
        assert "CREATE INDEX IF NOT EXISTS idx_memory_embedding_hnsw" in sql
        assert "USING hnsw (embedding vector_cosine_ops)" in sql
        assert "CREATE TABLE IF NOT EXISTS aio_memory_keywords" in sql


class TestVectorSearchSql:
    def test_vector_search_uses_cosine_distance(self, mocked_pgvector_backend):
        cur = mocked_pgvector_backend._test_cursor
        cur.executed.clear()
        cur.params.clear()
        mocked_pgvector_backend.vector_search([0.1] * 384, store_type="episodic", top_k=3)
        sql = " ".join(cur.executed)
        assert "<=>" in sql
        assert "vector" in sql.lower()

    def test_vector_search_returns_scores(self, mocked_pgvector_backend):
        cur = mocked_pgvector_backend._test_cursor
        cur._fetchall = [("e1", 0.95), ("e2", 0.88)]
        results = mocked_pgvector_backend.vector_search([0.1] * 384, top_k=2)
        assert results == [("e1", 0.95), ("e2", 0.88)]


class TestHybridSearchWeights:
    def test_hybrid_search_weights(self, mocked_pgvector_backend):
        cur = mocked_pgvector_backend._test_cursor
        cur.executed.clear()
        cur.params.clear()
        cur._fetchall = [("e1", 0.92)]
        results = mocked_pgvector_backend.hybrid_search(
            query_embedding=[0.1] * 384,
            keywords=["python", "asyncio"],
            store_type="long_term",
            top_k=5,
        )
        sql = " ".join(cur.executed)
        assert "0.6" in sql
        assert "0.4" in sql
        assert results == [("e1", 0.92)]

    def test_hybrid_search_fallback_when_no_keywords(self, mocked_pgvector_backend):
        with patch.object(mocked_pgvector_backend, "vector_search", return_value=[("e1", 0.9)]) as mock_vs:
            results = mocked_pgvector_backend.hybrid_search(
                query_embedding=[0.1] * 384,
                keywords=[],
                top_k=5,
            )
        mock_vs.assert_called_once_with([0.1] * 384, store_type=None, top_k=5)
        assert results == [("e1", 0.9)]


class TestPgvectorUnavailableDegradesToJsonb:
    def test_pgvector_unavailable_degrades_to_jsonb(self):
        with patch("aio.layers.memory_backends.PSYCOPG2_AVAILABLE", True):
            with patch("aio.layers.memory_backends._check_pgvector_sql", return_value=False):
                with patch("psycopg2.connect") as mock_connect:
                    cur = FakeCursor()
                    conn = FakeConn(cur)
                    mock_connect.return_value = conn
                    backend = PostgresBackend(
                        "postgresql://localhost/aio",
                        vector_dimension=384,
                        pgvector_enable=True,
                    )
                    assert backend._pgvector_active is False
                    sql = " ".join(cur.executed)
                    assert "payload JSONB NOT NULL" in sql
                    assert "embedding" not in sql


class TestConnectionFailureFallback:
    def test_connection_failure_fallback(self):
        with patch("aio.layers.memory_backends.PSYCOPG2_AVAILABLE", True):
            with patch("psycopg2.connect", side_effect=RuntimeError("connection refused")):
                backend = PostgresBackend(
                    "postgresql://localhost/aio",
                    vector_dimension=384,
                    pgvector_enable=True,
                )
                assert isinstance(backend, PostgresBackend)
                assert backend._conn is None
                assert backend._pgvector_active is False


class TestPsycopg2Unavailable:
    def test_psycopg2_unavailable_logs_warning(self, caplog):
        with patch("aio.layers.memory_backends.PSYCOPG2_AVAILABLE", False):
            with caplog.at_level("WARNING", logger="aio.layers.memory_backends"):
                backend = PostgresBackend("postgresql://localhost/aio")
        assert backend._conn is None
        assert "psycopg2 package not installed" in caplog.text.lower()

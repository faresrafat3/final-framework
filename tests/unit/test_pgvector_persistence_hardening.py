from unittest.mock import patch

from aio.layers.memory_backends import PostgresBackend


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.params = []
        self._fetchall = []

    def execute(self, sql, params=None):
        self.executed.append(sql)
        self.params.append(params)

    def fetchall(self):
        return self._fetchall

    def fetchone(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def _build_backend() -> tuple[PostgresBackend, FakeCursor]:
    with patch("aio.layers.memory_backends.PSYCOPG2_AVAILABLE", True):
        with patch("aio.layers.memory_backends._check_pgvector_sql", return_value=True):
            with patch("psycopg2.connect") as mock_connect:
                cursor = FakeCursor()
                conn = FakeConn(cursor)
                mock_connect.return_value = conn
                backend = PostgresBackend(
                    "postgresql://localhost/aio",
                    vector_dimension=384,
                    pgvector_enable=True,
                )
                return backend, cursor


def test_sync_uses_upsert_strategy_instead_of_table_truncate():
    backend, cursor = _build_backend()
    cursor.executed.clear()
    cursor.params.clear()

    backend.episodic["e1"] = {
        "id": "e1",
        "content": "episodic event",
        "embedding": [0.1] * 384,
        "timestamp": 1.0,
        "importance": 0.5,
    }
    backend.sync()

    joined_sql = "\n".join(cursor.executed)
    assert "ON CONFLICT" in joined_sql
    assert "DELETE FROM aio_memory_entries" not in joined_sql


def test_vector_search_casts_query_to_vector_literal_string():
    backend, cursor = _build_backend()
    cursor.executed.clear()
    cursor.params.clear()
    cursor._fetchall = [("e1", 0.9)]

    result = backend.vector_search([0.1] * 384, top_k=1)

    assert result == [("e1", 0.9)]
    first_param = cursor.params[-1][0]
    assert isinstance(first_param, str)
    assert first_param.startswith("[")

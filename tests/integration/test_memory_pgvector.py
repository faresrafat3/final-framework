import os
import time

import pytest

from aio import MemoryBridge, MemoryConfig, ObservabilityLayer, ObservabilityConfig, make_initial_state


def _has_postgres() -> bool:
    url = os.getenv("POSTGRES_URL", "postgresql://localhost/aio")
    try:
        import psycopg2
        conn = psycopg2.connect(url)
        conn.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _has_postgres(), reason="Postgres not available")
class TestMemoryPgvectorFlow:
    def test_full_flow_with_pgvector(self):
        obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
        config = MemoryConfig(
            backend_type="postgres",
            postgres_url=os.getenv("POSTGRES_URL", "postgresql://localhost/aio"),
            pgvector_enable=True,
            vector_dimension=384,
            epiphany_ttl_seconds=1,
            consolidation_batch_size=2,
            retrieval_top_k=3,
            importance_threshold=0.3,
            forget_ttl_seconds=3600,
        )
        mem = MemoryBridge(config, obs)
        try:
            state = make_initial_state("python asyncio patterns")
            state["context_window"] = [
                {"role": "user", "content": "python asyncio patterns", "turn": 1},
            ]
            state = mem.encode(state)
            assert len(mem._episodic) >= 1

            state = mem.verify(state)

            state = mem.store(state)

            # Consolidation requires aged entries; skip or force old timestamp
            for entry in mem._episodic.values():
                entry["timestamp"] = time.time() - 10
            state = mem.consolidate(state)

            state["raw_input"] = "python asyncio"
            state = mem.retrieve(state)
            assert len(state["working_memory"]) > 0
            assert state["memory_confidence"] > 0.0
        finally:
            mem.close()

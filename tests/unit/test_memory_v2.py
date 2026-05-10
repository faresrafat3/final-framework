import math
from unittest.mock import MagicMock, patch

from aio.config.memory import MemoryConfig as CanonicalMemoryConfig
from aio.config.models import MemoryConfig as LegacyMemoryConfig
from aio.layers.memory import MemoryBridge as LegacyMemoryBridge
from aio.memory.bridge import MemoryBridge as CanonicalMemoryBridge
from aio.memory.embeddings import RealEmbeddingEngine


class FakeSentenceTransformer:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def get_sentence_embedding_dimension(self) -> int:
        return 3

    def encode(self, payload, convert_to_numpy=True):
        if isinstance(payload, list):
            return [self.encode(item, convert_to_numpy=convert_to_numpy) for item in payload]

        base = float((sum(ord(ch) for ch in str(payload)) % 5) + 1)
        return [base, base + 1.0, base + 2.0]


def _norm(vec):
    return math.sqrt(sum(v * v for v in vec))


def test_canonical_memory_paths_are_compatible():
    assert CanonicalMemoryBridge is LegacyMemoryBridge
    assert CanonicalMemoryConfig is LegacyMemoryConfig


def test_real_embedding_engine_lazy_loads_model():
    model_ctor = MagicMock(return_value=FakeSentenceTransformer("fake-model"))

    with patch("aio.memory.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True), patch(
        "aio.memory.embeddings.SentenceTransformer",
        model_ctor,
    ):
        engine = RealEmbeddingEngine(model_name="fake-model", enable_real=True)
        assert model_ctor.call_count == 0

        vec = engine.embed("hello")
        assert model_ctor.call_count == 1
        assert engine.is_real is True
        assert len(vec) == engine.dimension == 3
        assert abs(_norm(vec) - 1.0) < 1e-6


def test_real_embedding_engine_fallback_when_disabled():
    model_ctor = MagicMock(return_value=FakeSentenceTransformer("fake-model"))

    with patch("aio.memory.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True), patch(
        "aio.memory.embeddings.SentenceTransformer",
        model_ctor,
    ):
        engine = RealEmbeddingEngine(enable_real=False)
        v1 = engine.embed("same text")
        v2 = engine.embed("same text")

    assert model_ctor.call_count == 0
    assert engine.is_real is False
    assert len(v1) == engine.dimension
    assert v1 == v2
    assert abs(_norm(v1) - 1.0) < 1e-6


def test_real_embedding_engine_fallback_when_dependency_unavailable(caplog):
    with patch("aio.memory.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", False):
        with caplog.at_level("WARNING", logger="aio.memory.embeddings"):
            engine = RealEmbeddingEngine(enable_real=True)
            v1 = engine.embed("offline")
            v2 = engine.embed("offline")

    assert engine.is_real is False
    assert len(v1) == engine.dimension
    assert v1 == v2
    assert abs(_norm(v1) - 1.0) < 1e-6
    assert "falling back" in caplog.text.lower() or "not installed" in caplog.text.lower()


def test_real_embedding_engine_fallback_when_model_load_fails(caplog):
    with patch("aio.memory.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True), patch(
        "aio.memory.embeddings.SentenceTransformer",
        side_effect=RuntimeError("load failed"),
    ):
        with caplog.at_level("WARNING", logger="aio.memory.embeddings"):
            engine = RealEmbeddingEngine(enable_real=True)
            v1 = engine.embed("failure path")
            v2 = engine.embed("failure path")

    assert engine.is_real is False
    assert len(v1) == engine.dimension
    assert v1 == v2
    assert abs(_norm(v1) - 1.0) < 1e-6
    assert "load failed" in caplog.text.lower()


def test_real_embedding_engine_embed_batch_real_path():
    with patch("aio.memory.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True), patch(
        "aio.memory.embeddings.SentenceTransformer",
        return_value=FakeSentenceTransformer("fake-model"),
    ):
        engine = RealEmbeddingEngine(model_name="fake-model", enable_real=True)
        batch = engine.embed_batch(["alpha", "beta"])
        single = engine.embed("alpha")

    assert engine.is_real is True
    assert len(batch) == 2
    assert batch[0] == single
    assert all(abs(_norm(vec) - 1.0) < 1e-6 for vec in batch)


def test_real_embedding_engine_embed_batch_fallback_path():
    engine = RealEmbeddingEngine(enable_real=False)
    batch = engine.embed_batch(["x", "y", "x"])

    assert engine.is_real is False
    assert len(batch) == 3
    assert batch[0] == batch[2]
    assert batch[0] != batch[1]
    assert all(len(vec) == engine.dimension for vec in batch)
    assert all(abs(_norm(vec) - 1.0) < 1e-6 for vec in batch)

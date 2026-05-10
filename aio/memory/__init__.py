"""AIO Framework — Memory embedding engines, lifecycle engine, and bridge exports."""

from .embeddings import (
    BaseEmbeddingEngine,
    RealEmbeddingEngine,
    PseudoEmbeddingEngine,
    EmbeddingEngineFactory,
)
from .lifecycle import (
    LLMConsolidator,
    EbbinghausForgettingCurve,
    MemoryLifecycleEngine,
)


def __getattr__(name: str):
    if name == "MemoryBridge":
        from .bridge import MemoryBridge

        return MemoryBridge
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "MemoryBridge",
    "BaseEmbeddingEngine",
    "RealEmbeddingEngine",
    "PseudoEmbeddingEngine",
    "EmbeddingEngineFactory",
    "LLMConsolidator",
    "EbbinghausForgettingCurve",
    "MemoryLifecycleEngine",
]

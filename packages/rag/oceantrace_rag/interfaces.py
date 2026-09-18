from typing import Protocol

from oceantrace_common.models import Evidence
from pydantic import BaseModel


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate text from supplied evidence. Must not fabricate unseen facts."""

    def structured_generate(self, prompt: str, schema_name: str) -> dict[str, object]:
        """Generate structured output constrained by the requested schema."""

    def health_check(self) -> bool:
        """Return whether the local provider is reachable."""


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed documents or queries with a local model."""


class RerankerProvider(Protocol):
    def rerank(self, query: str, evidence: list[Evidence]) -> list[Evidence]:
        """Rerank retrieved evidence without changing provenance."""


class RAGSearchResult(BaseModel):
    evidence: Evidence
    score: float


class RAGRetriever(Protocol):
    def search(self, query: str, limit: int = 5) -> list[RAGSearchResult]:
        """Run hybrid retrieval and preserve citations."""


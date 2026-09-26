"""Embedding provider abstraction.

The application never imports a specific vendor. `get_embedding_provider()` reads the
configured provider name and returns an implementation of `EmbeddingProvider`.
"""
import hashlib
import math
from app.config import get_settings


class EmbeddingProvider:
    name = "base"

    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_image(self, image_url: str) -> list[float] | None:
        """Return None if the provider is text-only."""
        return None


class HashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic, dependency-free character n-gram + token hashing embedding.

    Good enough to capture lexical similarity for an MVP. Replace with OpenAI /
    sentence-transformers / CLIP text encoder for semantic similarity.
    """
    name = "hashing"

    def __init__(self, dims: int = 512):
        self.dims = dims

    def _bucket(self, s: str) -> int:
        return int(hashlib.md5(s.encode()).hexdigest()[:8], 16) % self.dims

    def embed_text(self, text: str) -> list[float]:
        from app.services.normalizer import tokens
        vec = [0.0] * self.dims
        toks = tokens(text)
        for t in toks:
            vec[self._bucket("w:" + t)] += 2.0
            padded = f"#{t}#"
            for i in range(len(padded) - 2):
                vec[self._bucket("g:" + padded[i:i + 3])] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Stub for OpenAI text-embedding-3-small. Requires OPENAI_API_KEY and the `openai` package."""
    name = "openai"

    def __init__(self, api_key: str):
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.api_key = api_key

    def embed_text(self, text: str) -> list[float]:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise RuntimeError("pip install openai to use the OpenAI embedding provider") from e
        client = OpenAI(api_key=self.api_key)
        r = client.embeddings.create(model="text-embedding-3-small", input=text)
        return list(r.data[0].embedding)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return max(0.0, min(1.0, dot / (na * nb)))


_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        s = get_settings()
        if s.embedding_provider == "openai":
            _provider = OpenAIEmbeddingProvider(s.openai_api_key)
        else:
            _provider = HashingEmbeddingProvider()
    return _provider

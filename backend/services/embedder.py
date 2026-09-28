import numpy as np


class BaseEmbedder:
    """Base interface for embedding models."""

    def embed(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError("Embedder must implement embed(texts)")


class BGELazyEmbedder(BaseEmbedder):
    """
    Lazy singleton embedder that loads BAAI/bge-small-en-v1.5 on the first call.
    Returns L2-normalized float32 vectors so cosine similarity equals dot product.
    """
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            from sentence_transformers import SentenceTransformer
            # Load BAAI/bge-small-en-v1.5 model once
            cls._model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        return cls._model

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        model = self.get_model()
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.astype(np.float32)


class FakeEmbedder(BaseEmbedder):
    """
    Lightweight deterministic embedder for unit and integration testing without downloading models.
    Uses token-based bag-of-words hashing to generate consistent, unit-normalized vectors.
    """
    def __init__(self, dim: int = 1024):
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        import re
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        vectors = []
        for text in texts:
            words = [w for w in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(w) > 1]
            vec = np.zeros(self.dim, dtype=np.float32)
            if not words:
                vec[0] = 1.0
            else:
                for word in words:
                    idx = abs(hash(word)) % self.dim
                    vec[idx] += 1.0
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                else:
                    vec[0] = 1.0
            vectors.append(vec)

        return np.array(vectors, dtype=np.float32)


# Active embedder instance
_ACTIVE_EMBEDDER: BaseEmbedder | None = None


def get_embedder() -> BaseEmbedder:
    """Get the current embedder instance (defaults to lazy BAAI embedder)."""
    global _ACTIVE_EMBEDDER
    if _ACTIVE_EMBEDDER is None:
        _ACTIVE_EMBEDDER = BGELazyEmbedder()
    return _ACTIVE_EMBEDDER


def set_embedder(embedder: BaseEmbedder):
    """Set custom embedder (e.g. FakeEmbedder for tests)."""
    global _ACTIVE_EMBEDDER
    _ACTIVE_EMBEDDER = embedder


def reset_embedder():
    """Reset back to default lazy embedder."""
    global _ACTIVE_EMBEDDER
    _ACTIVE_EMBEDDER = None


def embed(texts: list[str]) -> np.ndarray:
    """Convenience function to embed a list of strings using the active embedder."""
    return get_embedder().embed(texts)

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from app.settings import settings


@dataclass
class EmbeddingClient:
    model_name: str
    backend: str

    @staticmethod
    def from_settings() -> "EmbeddingClient":
        backend = settings.embed_backend.lower().strip()
        if backend == "ollama":
            return OllamaEmbeddingClient(settings.ollama_embed_model)
        if backend == "openai":
            key = settings.openai_api_key
            if not key:
                raise ValueError("EV_OPENAI_API_KEY is not set. Required when EV_EMBED_BACKEND=openai.")
            return OpenAIEmbeddingClient(api_key=key)
        if backend == "sentence_transformers":
            return SentenceTransformerEmbeddingClient(settings.st_model, settings.st_model_local_path)
        if backend == "hash":
            return HashEmbeddingClient()
        raise ValueError(f"Unknown EV_EMBED_BACKEND: {settings.embed_backend}. Options: hash | openai | ollama | sentence_transformers")

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        raise NotImplementedError


class OllamaEmbeddingClient(EmbeddingClient):
    def __init__(self, model: str):
        super().__init__(model_name=model, backend="ollama")

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings via Ollama.

        Ollama's current API uses POST /api/embed with body:
            {"model": "...", "input": "text" | ["text1","text2",...]}

        Older Ollama builds used POST /api/embeddings with body:
            {"model": "...", "prompt": "..."}

        We try the modern endpoint first, then fall back.
        """
        import requests

        base = settings.ollama_base_url.rstrip("/")

        # ---- Preferred (modern) endpoint: /api/embed ----
        try:
            r = requests.post(
                f"{base}/api/embed",
                json={"model": self.model_name, "input": texts},
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            embs = data.get("embeddings")
            if not isinstance(embs, list):
                raise ValueError(f"Unexpected response (missing 'embeddings'): {list(data.keys())}")
            return np.array(embs, dtype=np.float32)
        except Exception as e_embed:
            # ---- Legacy fallback endpoint: /api/embeddings ----
            try:
                vecs = []
                url = f"{base}/api/embeddings"
                for t in texts:
                    rr = requests.post(url, json={"model": self.model_name, "prompt": t}, timeout=120)
                    rr.raise_for_status()
                    dd = rr.json()
                    if "embedding" in dd:
                        vecs.append(dd["embedding"])
                    elif "embeddings" in dd and isinstance(dd["embeddings"], list) and dd["embeddings"]:
                        vecs.append(dd["embeddings"][0])
                    else:
                        raise ValueError(f"Unexpected legacy response keys: {list(dd.keys())}")
                return np.array(vecs, dtype=np.float32)
            except Exception as e_legacy:
                raise RuntimeError(
                    "Ollama embeddings failed. Tried /api/embed then /api/embeddings. "
                    f"First error: {e_embed}. Second error: {e_legacy}."
                )


class SentenceTransformerEmbeddingClient(EmbeddingClient):
    def __init__(self, model_name: str, local_path: str | None):
        super().__init__(model_name=model_name, backend="sentence_transformers")
        self._model_name = model_name
        self._local_path = local_path
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer
        name = self._local_path if (self._local_path and len(self._local_path.strip()) > 0) else self._model_name
        self._model = SentenceTransformer(name)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        self._load()
        emb = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.array(emb, dtype=np.float32)


class OpenAIEmbeddingClient(EmbeddingClient):
    """Embeddings via OpenAI API (text-embedding-3-small). Great semantic quality, no local GPU needed."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        super().__init__(model_name=model, backend="openai")
        self._api_key = api_key

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        import requests
        if not texts:
            return np.zeros((0, 1536), dtype=np.float32)
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        r = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers=headers,
            json={"model": self.model_name, "input": texts},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        vecs = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
        return np.array(vecs, dtype=np.float32)


class HashEmbeddingClient(EmbeddingClient):
    """Deterministic local fallback embeddings (no external models).

    Useful for demos, offline smoke tests, or when Ollama / sentence-transformers
    are not available. Not semantically meaningful like real embeddings.
    """

    def __init__(self, dims: int = 384):
        super().__init__(model_name=f"hash-{dims}", backend="hash")
        self.dims = int(dims)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        import hashlib
        vecs = []
        for t in texts:
            b = (t or '').encode('utf-8', errors='ignore')
            h = hashlib.sha256(b).digest()
            seed = int.from_bytes(h[:8], 'big', signed=False)
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(self.dims).astype(np.float32)
            n = float(np.linalg.norm(v) + 1e-9)
            v = v / n
            vecs.append(v)
        return np.vstack(vecs) if vecs else np.zeros((0, self.dims), dtype=np.float32)

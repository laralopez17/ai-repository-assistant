class FakeEmbeddingProvider:
    _KEYWORD_VECTORS: dict[str, list[float]] = {
        "scanner": [1.0, 0.0, 0.0],
        "chunk": [0.0, 1.0, 0.0],
        "config": [0.0, 0.0, 1.0],
    }

    @property
    def model_name(self) -> str:
        return "fake-embedding-model"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_single(text) for text in texts]

    def embed_text(self, text: str) -> list[float]:
        return self._embed_single(text)

    def _embed_single(self, text: str) -> list[float]:
        lower_text = text.lower()
        for keyword, vector in self._KEYWORD_VECTORS.items():
            if keyword in lower_text:
                return vector.copy()
        return [0.0, 0.0, 0.0]

from typing import Protocol


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str:
        ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_text(self, text: str) -> list[float]:
        ...

from typing import Protocol

from app.domain.models import SearchResult


class LLMProvider(Protocol):
    def generate_answer(self, question: str, context_chunks: list[SearchResult]) -> str:
        ...

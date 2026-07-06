from app.domain.models import SearchResult

INSUFFICIENT_CONTEXT_ANSWER = (
    "There is not enough context in the indexed repository to answer this question."
)


class FakeLLMProvider:
    def generate_answer(self, question: str, context_chunks: list[SearchResult]) -> str:
        if not context_chunks:
            return INSUFFICIENT_CONTEXT_ANSWER

        top_chunk = context_chunks[0]
        return (
            f"The relevant logic appears in `{top_chunk.file_path}` "
            f"(lines {top_chunk.start_line}-{top_chunk.end_line}). "
            f"Question: {question}"
        )

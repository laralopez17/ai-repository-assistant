from app.domain.models import SearchResult

SYSTEM_PROMPT = """You are a technical assistant answering questions about a code repository.
Answer only using the provided context chunks.
Do not invent files, classes, functions, dependencies, or behavior that are not supported by the context.
If the context is insufficient, say clearly that there is not enough information.
Mention relevant file paths and line ranges when explaining.
Keep the answer concise and technical."""


def build_user_prompt(question: str, context_chunks: list[SearchResult]) -> str:
    context_blocks: list[str] = []
    for index, chunk in enumerate(context_chunks, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"[Chunk {index}]",
                    f"File: {chunk.file_path}",
                    f"Lines: {chunk.start_line}-{chunk.end_line}",
                    f"Source type: {chunk.source_type}",
                    "Content:",
                    chunk.content,
                ]
            )
        )

    context_text = "\n\n".join(context_blocks)
    return (
        f"Question:\n{question}\n\n"
        f"Context chunks:\n{context_text}\n\n"
        "Answer the question using only the context above."
    )

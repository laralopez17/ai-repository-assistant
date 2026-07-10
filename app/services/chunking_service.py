from app.core.errors import InvalidChunkingConfigError
from app.domain.models import ContentChunk, FileContent
from app.utils.source_type import detect_source_type


class ChunkingService:
    def __init__(self, max_chars_per_chunk: int) -> None:
        if max_chars_per_chunk <= 0:
            raise InvalidChunkingConfigError(
                "max_chars_per_chunk must be greater than 0"
            )
        self._max_chars_per_chunk = max_chars_per_chunk

    def chunk_files(
        self,
        files: list[FileContent],
        max_lines_per_chunk: int,
        overlap_lines: int,
    ) -> list[ContentChunk]:
        self._validate_chunking_params(max_lines_per_chunk, overlap_lines)

        chunks: list[ContentChunk] = []
        for file_content in files:
            chunks.extend(
                self._chunk_file(file_content, max_lines_per_chunk, overlap_lines)
            )

        return chunks

    def _validate_chunking_params(
        self,
        max_lines_per_chunk: int,
        overlap_lines: int,
    ) -> None:
        if overlap_lines >= max_lines_per_chunk:
            raise InvalidChunkingConfigError(
                "overlap_lines must be smaller than max_lines_per_chunk"
            )

    def _chunk_file(
        self,
        file_content: FileContent,
        max_lines_per_chunk: int,
        overlap_lines: int,
    ) -> list[ContentChunk]:
        total_lines = len(file_content.lines)
        if total_lines == 0:
            return []

        normalized_path = file_content.file_path.replace("\\", "/")
        source_type = detect_source_type(normalized_path, file_content.extension)
        step = max_lines_per_chunk - overlap_lines
        chunks: list[ContentChunk] = []
        start_line = 1
        chunk_index = 0

        while start_line <= total_lines:
            end_line = min(start_line + max_lines_per_chunk - 1, total_lines)
            chunk_lines = file_content.lines[start_line - 1 : end_line]
            content = "\n".join(chunk_lines)
            content_parts = self._split_oversized_content(content)

            for part in content_parts:
                chunks.append(
                    ContentChunk(
                        chunk_id=f"{normalized_path}::chunk-{chunk_index:03d}",
                        file_path=normalized_path,
                        extension=file_content.extension,
                        start_line=start_line,
                        end_line=end_line,
                        content=part,
                        source_type=source_type,
                    )
                )
                chunk_index += 1

            if end_line == total_lines:
                break

            start_line += step

        return chunks

    def _split_oversized_content(self, content: str) -> list[str]:
        if len(content) <= self._max_chars_per_chunk:
            return [content]

        parts: list[str] = []
        start = 0
        while start < len(content):
            end = start + self._max_chars_per_chunk
            parts.append(content[start:end])
            start = end
        return parts

from pathlib import Path

from app.domain.models import ExtractionResult, FileContent, ScannedFile, SkippedFile


class ContentExtractor:
    def extract(self, repository_path: str, files: list[ScannedFile]) -> ExtractionResult:
        root = Path(repository_path)
        extracted_files: list[FileContent] = []
        skipped_files: list[SkippedFile] = []

        for scanned_file in files:
            file_path = root / scanned_file.relative_path
            lines, skip_reason = self._read_text_lines(file_path)

            if skip_reason is not None:
                skipped_files.append(
                    SkippedFile(
                        file_path=scanned_file.relative_path,
                        reason=skip_reason,
                    )
                )
                continue

            extracted_files.append(
                FileContent(
                    file_path=scanned_file.relative_path,
                    extension=scanned_file.extension,
                    lines=lines,
                )
            )

        return ExtractionResult(
            files=sorted(extracted_files, key=lambda file: file.file_path),
            skipped_files=sorted(skipped_files, key=lambda file: file.file_path),
        )

    def _read_text_lines(self, path: Path) -> tuple[list[str] | None, str | None]:
        try:
            with path.open("r", encoding="utf-8", errors="strict") as handle:
                lines = [line.rstrip("\n\r") for line in handle]
        except UnicodeDecodeError:
            return None, "cannot decode as utf-8"
        except OSError:
            return None, "cannot read file"

        return lines, None

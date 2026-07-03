# AI Repository Assistant — Project Notes

## Goal

Build a backend-first AI application that can analyze code repositories and answer questions about their structure, files, and architecture.

## Positioning

Portfolio project for Backend / AI Applications Engineer roles.

## Current Milestone

### Milestone 2 — Repository Content Extraction & Chunking

Implemented on top of Milestone 1:

- `POST /repositories/chunks` endpoint
- `ContentExtractor` for safe UTF-8 file reading with skipped-file traceability
- `ChunkingService` for line-based chunking with overlap
- Domain models: `FileContent`, `ContentChunk`, `SkippedFile`, `ChunkingResult`
- Tests for extraction, chunking, and API behavior

Still excluded: LLM APIs, embeddings, vector databases, agents, MCP, Docker.

### Milestone 1 — Completed

Implemented the FastAPI backend foundation with:

- Health check endpoint
- Local repository scan endpoint
- Clean layered structure
- Repository scanner service
- File filtering for generated/cache directories
- Basic pytest coverage

Next milestone:
Prepare repository content for indexing by extracting readable source files and creating chunks with metadata.

## Tech Stack

- Python
- FastAPI
- Pydantic
- pytest
- Docker later
- LLM/RAG later

## Architecture Decisions

### Layered boundaries

| Layer        | Responsibility                                             |
| ------------ | ---------------------------------------------------------- |
| `api/routes` | HTTP only: request parsing, status codes, response mapping |
| `schemas`    | Pydantic models for API input/output                       |
| `domain`     | Internal dataclasses with no FastAPI dependency            |
| `services`   | Business logic (scanning, extraction, chunking)            |
| `utils`      | Small reusable helpers (file filtering, line counting)     |
| `core`       | Shared config and domain errors                            |

### Scanner behavior

- Walks the filesystem recursively from the resolved absolute path.
- Skips known noise directories: `.git`, `node_modules`, `dist`, `build`, `target`, `venv`, `.venv`, `__pycache__`, `.idea`, `.vscode`.
- Skips binary files (null-byte detection) and files larger than 1 MB.
- Counts lines only for readable UTF-8 text files.
- Aggregates extension counts into `languages`.
- Records which ignored directories were encountered during the walk.

### Error handling

- Missing path → `404` with `PathNotFoundError` message.
- Path exists but is not a directory → `400` with `NotADirectoryError` message.
- Errors are raised in `services`, mapped to HTTP in `api/routes`.

### Dependency injection

- `RepositoryScanner` is injected via FastAPI `Depends` in the scan route to keep routes testable and swappable later.

### What we intentionally avoided

- No database (scan results are ephemeral).
- No GitHub API (local paths first).
- No LLM/RAG/agents yet.
- No Docker yet.

## Learning Goals

- Recover Python fluency.
- Practice clean backend structure.
- Build confidence reading and reviewing AI-generated code.

## Next Steps (Milestone 3+)

1. Embed chunks and store vectors for retrieval.
2. Add query endpoint backed by vector search.
3. Add persistence for scan/chunk results (SQLite or Postgres).
4. Integrate GitHub API for remote repository ingestion.
5. Add Docker and deployment configuration.
6. Introduce agent orchestration once basic RAG is stable.

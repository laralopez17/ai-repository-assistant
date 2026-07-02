# AI Repository Assistant — Project Notes

## Goal

Build a backend-first AI application that can analyze code repositories and answer questions about their structure, files, and architecture.

## Positioning

Portfolio project for Backend / AI Applications Engineer roles.

## Current Milestone

Milestone 1 — FastAPI backend base without AI.

Delivered in this milestone:

- `GET /health` endpoint
- `POST /repositories/scan` endpoint
- Local repository scanner with ignored directories and file filtering
- Layered architecture ready for future RAG and agents
- pytest coverage for health, scanner, and API error paths

## Tech Stack

- Python
- FastAPI
- Pydantic
- pytest
- Docker later
- LLM/RAG later

## Architecture Decisions

### Layered boundaries

| Layer | Responsibility |
|-------|----------------|
| `api/routes` | HTTP only: request parsing, status codes, response mapping |
| `schemas` | Pydantic models for API input/output |
| `domain` | Internal dataclasses with no FastAPI dependency |
| `services` | Business logic (repository scanning) |
| `utils` | Small reusable helpers (file filtering, line counting) |
| `core` | Shared config and domain errors |

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

## Next Steps (Milestone 2+)

1. Add persistence for scan results (SQLite or Postgres).
2. Chunk and embed file contents for RAG.
3. Add query endpoint backed by vector search.
4. Integrate GitHub API for remote repository ingestion.
5. Add Docker and deployment configuration.
6. Introduce agent orchestration once basic RAG is stable.

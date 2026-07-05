# AI Repository Assistant — Project Notes

## Goal

Build a backend-first AI application that can analyze code repositories and answer questions about their structure, files, and architecture.

## Positioning

Portfolio project for Backend / AI Applications Engineer roles.

## Current Milestone

### Milestone 3 — Embeddings + In-Memory Semantic Search

Implemented on top of Milestones 1 and 2:

- `EmbeddingProvider` abstraction with OpenAI, Gemini, and fake providers
- `VectorStore` with in-memory cosine similarity search
- `RepositoryIndexer` orchestrating scan → extract → chunk → embed → store
- `SemanticSearchService` for query embedding and ranked retrieval
- `POST /repositories/index` and `POST /repositories/search` endpoints
- Tests use `FakeEmbeddingProvider` only; no external API calls in CI

Still excluded: LLM answer generation, RAG synthesis, agents, MCP, Docker, external vector DB.

### Milestone 2 — Completed

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

| Layer        | Responsibility                                                      |
| ------------ | ------------------------------------------------------------------- |
| `api/routes` | HTTP only: request parsing, status codes, response mapping          |
| `schemas`    | Pydantic models for API input/output                                |
| `domain`     | Internal dataclasses with no FastAPI dependency                     |
| `services`   | Business logic (scanning, extraction, chunking, embeddings, search) |
| `utils`      | Small reusable helpers (file filtering, line counting)              |
| `core`       | Shared config and domain errors                                     |

### Scanner behavior

- Walks the filesystem recursively from the resolved absolute path.
- Skips known noise directories: `.git`, `node_modules`, `dist`, `build`, `target`, `venv`, `.venv`, `__pycache__`, `.pytest_cache`, `.idea`, `.vscode`.
- Skips sensitive files before any content processing: `.env`, `.env.local`, `.env.*`, `*.pem`, `*.key`, `id_rsa`, `id_ed25519`, `credentials.json`, `secrets.json`.
- Skips binary files (null-byte detection) and files larger than 1 MB.
- Counts lines only for readable UTF-8 text files.
- Aggregates extension counts into `languages`.
- Records ignored directories and ignored sensitive files in scan results.

### Secret file exclusion

Sensitive files are excluded at scan time, so they never flow into chunking or embedding. This prevents API keys and credentials from being indexed or returned in search results.

Never commit `.env` files. Treat repository scanning as untrusted input when pointing at unknown paths.

### Error handling

- Missing path → `404` with `PathNotFoundError` message.
- Path exists but is not a directory → `400` with `NotADirectoryError` message.
- Index not found → `404`.
- Chunk limit exceeded → `400` before embedding API calls.
- OpenAI quota/billing exceeded → `402`.
- OpenAI rate limit → `429`.
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

### Embedding providers

- `EmbeddingProvider` protocol defines `embed_text` / `embed_texts` and `model_name`.
- `get_embedding_provider()` selects OpenAI, Gemini, or `fake` via `EMBEDDING_PROVIDER`.
- Indexer and search depend only on the protocol, not on a specific vendor.
- `FakeEmbeddingProvider` maps keywords (`scanner`, `chunk`, `config`) to deterministic vectors for tests and local dev.

### Local development with fake provider

Set `EMBEDDING_PROVIDER=fake` in `.env` to index and search without OpenAI or Gemini. No API key required.

### OpenAI quota / billing errors

`OpenAIEmbeddingProvider` catches OpenAI `RateLimitError` and maps quota issues to `EmbeddingProviderError` with HTTP `402`. Rate limits without quota exhaustion return HTTP `429`. The API never exposes raw OpenAI exceptions.

### Indexing safety limit

`MAX_CHUNKS_TO_EMBED` (default `50`) is checked in `RepositoryIndexer` before calling the embedding provider. Repositories exceeding this limit return `400` without incurring API cost.

### Vector store

- In-memory store keyed by `index_id`.
- Cosine similarity via numpy; results sorted by descending score.
- Chunks carry `source_type` metadata (`source`, `test`, `docs`, `config`, `other`).
- Search accepts `include_tests` (default `true`) to filter out test chunks after similarity ranking.
- No persistence yet; indexes live for the process lifetime.

## Next Steps (Milestone 4+)

1. Add RAG query endpoint with LLM answer synthesis and citations.
2. Add persistence for indexes (SQLite or Postgres).
3. Integrate GitHub API for remote repository ingestion.
4. Add Docker and deployment configuration.
5. Introduce agent orchestration once basic RAG is stable.

# AI Repository Assistant — Project Notes

## Goal

Build a backend-first AI application that can analyze code repositories and answer questions about their structure, files, and architecture.

## Positioning

Portfolio project for Backend / AI Applications Engineer roles.

## Current Milestone

### Milestone 5 — SQLite Persistence + Index Management (implemented; pending manual verification)

Implemented on top of Milestones 1–4:

- `IndexStore` protocol with `SQLiteIndexStore` as the single source of truth
- SQLite schema for `indexes` and `chunks` with cascade delete
- Embeddings stored as JSON; cosine similarity in `app/utils/similarity.py`
- Index management endpoints: list, get, delete
- `/repositories/search` and `/repositories/ask` read from SQLite after restart
- Tests use temporary SQLite files only

Intentionally deferred: in-memory cache, ORM, Postgres/pgvector.

### Milestone 4 — Completed

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

### What we intentionally avoided (historical / still out of scope)

- No GitHub API (local paths first).
- No agents or MCP in v1.
- No Docker yet (planned for v1 polish).
- No in-memory cache in M5.

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

### SQLite persistence

- `SQLITE_DB_PATH` (default `./data/ai_repository_assistant.db`) is the single source of truth.
- `RepositoryIndexer` and `SemanticSearchService` depend on the `IndexStore` protocol, not SQLite directly.
- `SQLiteIndexStore.search()` loads chunks from disk, computes cosine similarity in Python, filters `include_tests`, ranks, and returns `top_k`.
- Raises `IndexNotFoundError` before returning empty results when the index does not exist.
- `created_at` uses timezone-aware UTC ISO timestamps.
- `data/` and `*.db` files are gitignored.

### Future performance work (deferred)

- In-memory cache in front of SQLite for hot indexes
- Postgres + pgvector if scale requires it
- Incremental reindexing

### RAG answering

- `/repositories/search` returns ranked chunks only.
- `/repositories/ask` reuses `SemanticSearchService`, then calls `LLMProvider` to synthesize a grounded answer.
- Prompt templates live in `rag_prompt.py`; providers only handle API calls.
- Sources are returned separately from the answer (metadata only, no chunk body in citations).
- If retrieval returns no chunks, the service answers with a safe insufficient-context message without calling the LLM.

## Next Steps (post-M5 / v1 polish)

1. Docker and developer setup documentation
2. Manual demo flow verification end-to-end
3. Integrate GitHub API for remote repository ingestion (future)
4. Introduce agent orchestration only after v1 is stable (future)

### Project Scope Rule

This project must reach a clear product-complete v1 instead of becoming an endless experiment.

The goal is to build a complete backend-first AI repository assistant with a defined finish line. Future scalability is important, but advanced ideas should be documented as future improvements unless they are part of the current milestone scope.

### Product-complete v1 target

The project is considered complete for portfolio v1 when it includes:

- FastAPI backend foundation
- Local repository scanning
- Sensitive file exclusion
- Content extraction and chunking
- Embedding provider abstraction
- Semantic search
- RAG answering with citations
- SQLite persistence and index management
- Docker/developer setup
- A clear demo flow
- Professional README, architecture notes and future improvements

Out of scope for v1 unless explicitly promoted later:

- Multi-user authentication
- Cloud deployment
- Advanced agents
- MCP integration
- Full UI
- Postgres/pgvector migration
- In-memory cache optimization
- Incremental reindexing

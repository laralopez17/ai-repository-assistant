# AI Repository Assistant — Project Notes

## Goal

Build a backend-first AI application that can analyze code repositories and answer questions about their structure, files, and architecture.

## Positioning

Portfolio project for Backend / AI Applications Engineer roles.

## Milestones

### Milestone 6 — Docker + Developer Experience (completed)

**Problem Docker solves:** New contributors should not need to guess Python version, virtualenv steps, or dependency installs. Docker provides a reproducible local runtime with the same FastAPI app, env-driven providers, and persisted SQLite indexes.

**Added:**

- `Dockerfile` for the FastAPI backend (Python 3.11-slim, uvicorn)
- `.dockerignore` to keep secrets, venvs, caches, and local DB files out of the image
- `docker-compose.yml` with port mapping, `.env` loading, and `./data` bind mount for SQLite
- README quickstart for local and Docker workflows, curl demo flow, and env variable reference
- Default fake providers in `.env.example` so manual verification needs no paid API keys

**Out of scope for M6:** cloud deployment, CI/CD, Kubernetes, production hardening, new AI features.

**Future production/deployment improvements (deferred):** managed hosting (Render/Railway/Fly.io/AWS), secrets manager, health/readiness probes for orchestrators, multi-stage image builds, non-root container user, Postgres if SQLite limits are hit.

### Milestone 5 — SQLite Persistence + Index Management (completed)

Implemented on top of Milestones 1–4:

- `IndexStore` protocol with `SQLiteIndexStore` as the single source of truth
- SQLite schema for `indexes` and `chunks` with cascade delete
- Embeddings stored as JSON; cosine similarity in `app/utils/similarity.py`
- Index management endpoints: list, get, delete
- `/repositories/search` and `/repositories/ask` read from SQLite after restart
- Tests use temporary SQLite files only

Intentionally deferred: in-memory cache, ORM, Postgres/pgvector.

### Milestone 4 — RAG Answering with Citations (completed)

Implemented on top of Milestones 1–3:

- `LLMProvider` protocol with OpenAI, Gemini, and fake providers
- `get_llm_provider()` factory driven by `LLM_PROVIDER`
- `RAGAnswerService` orchestrating semantic search + grounded answer generation
- `rag_prompt.py` for prompt construction; providers handle API calls only
- `POST /repositories/ask` returning `answer` and `sources` (metadata citations, no chunk body)
- Insufficient-context path returns a safe message without calling the LLM
- Tests use fake providers only; no external API calls in CI

Still excluded at this stage: agents, tool calling, MCP, persistence (added in M5).

### Milestone 3 — Embeddings + Semantic Search (completed)

Implemented on top of Milestones 1–2:

- `EmbeddingProvider` protocol with OpenAI, Gemini, and fake providers
- `get_embedding_provider()` factory driven by `EMBEDDING_PROVIDER`
- `RepositoryIndexer` for scan → extract → chunk → embed → store
- `SemanticSearchService` for query embedding and ranked retrieval
- `POST /repositories/index` and `POST /repositories/search`
- `source_type` metadata (`source`, `test`, `docs`, `config`, `other`) via `app/utils/source_type.py`
- `include_tests` filtering on search results
- `MAX_CHUNKS_TO_EMBED` safety cap checked before embedding API calls
- `EmbeddingProviderError` mapping OpenAI quota to HTTP `402` and rate limits to `429`
- `FakeEmbeddingProvider` for deterministic local dev and tests

Originally used an in-memory vector store; replaced by SQLite persistence in M5.

### Milestone 2 — Content Extraction + Chunking (completed)

Implemented on top of Milestone 1:

- `ContentExtractor` for reading scanned text files into `FileContent`
- `ChunkingService` for line-based chunking with configurable overlap
- `POST /repositories/chunks` endpoint
- Domain models: `FileContent`, `ContentChunk`, `SkippedFile`, `ChunkingResult`
- Skipped files recorded with explicit `reason` (binary, unreadable, sensitive, etc.)
- `chunk_id` format: `{normalized_path}::chunk-000`
- Overlap validation: `overlap_lines` must be less than `max_lines_per_chunk` (Pydantic + service)

Prepared repository content for embedding and search in M3.

### Milestone 1 — Backend Foundation + Repository Scanner (completed)

Initial FastAPI backend:

- `GET /health` health check
- `POST /repositories/scan` for local repository analysis
- `RepositoryScanner` walking the filesystem recursively
- Ignored directories: `.git`, `node_modules`, `dist`, `build`, `target`, venvs, caches, IDE folders
- Sensitive file exclusion: `.env`, `.env.*`, `*.pem`, `*.key`, `id_rsa`, `credentials.json`, etc.
- Binary detection (null-byte sample) and 1 MB file size cap
- Line counting and `languages` aggregation by extension
- Layered structure: `api/routes`, `schemas`, `domain`, `services`, `core`, `utils`
- Domain errors raised in services, mapped to HTTP status codes in routes
- Basic pytest coverage for scanner and API endpoints

## Current Milestone

Milestone 6 is complete. v1 portfolio polish: verify the full demo flow end-to-end and treat remaining items in **Next Steps** as future work unless promoted.

## Tech Stack

- Python
- FastAPI
- Pydantic
- pytest
- Docker (local development only)

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
- No cloud deployment in v1.
- No in-memory cache in M5+.

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

### Docker (local development)

- `Dockerfile` builds a Python 3.11 image with `requirements.txt` dependencies.
- `docker-compose.yml` runs the API on port 8000, loads `.env`, and overrides `SQLITE_DB_PATH` to `/app/data/ai_repository_assistant.db` (even if `.env` uses a local relative path).
- Host `./data` is bind-mounted to `/app/data`; indexes persist across container restarts as long as `./data` is kept on the host.
- `${REPO_MOUNT_SOURCE:-.}:/workspace:ro` mounts a repository read-only at `/workspace`; set `REPO_MOUNT_SOURCE` to index a different repo, always using `{"path": "/workspace"}` in API requests.
- `.env` is gitignored and excluded from the image; `.env.example` defaults to `EMBEDDING_PROVIDER=fake` and `LLM_PROVIDER=fake`.
- Docker is not production deployment; it standardizes the local developer experience.

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

## Next Steps (post-v1)

1. Integrate GitHub API for remote repository ingestion (future)
2. Introduce agent orchestration only after v1 is stable (future)
3. Production deployment patterns (hosting, secrets, observability) when scope expands beyond portfolio v1

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

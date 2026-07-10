# AI Repository Assistant — Project Notes

## Goal

Build a backend-first AI application that can analyze code repositories and answer questions about their structure, files, and architecture.

## Positioning

Portfolio project for Backend / AI Applications Engineer roles.

## Project status

**Portfolio v1 complete after M9.**

- M1–M9 delivered
- M8 manually verified with fake providers and OpenAI
- M9 closed documentation and presentation for portfolio readiness
- Advanced ideas below are **post-v1 future improvements**, not open required milestones

## Project Scope Rule

This project must reach a clear product-complete v1 instead of becoming an endless experiment.

The goal is a complete backend-first AI repository assistant with a defined finish line. Future scalability matters, but advanced ideas are documented as optional improvements unless explicitly promoted into a new milestone.

**v1 is closed after M9.** New work should be treated as a separate post-v1 effort.

## Product-complete v1 checklist

Delivered:

- FastAPI backend foundation
- Local repository scanning
- Sensitive file exclusion
- Content extraction and chunking
- Embedding provider abstraction
- Semantic search
- RAG answering with citations
- SQLite persistence and index management
- Docker / developer setup
- Public GitHub ingestion
- Clear CLI demo flow
- Professional README, architecture notes, limitations, and future work

Explicitly out of scope for v1:

- Multi-user authentication
- Cloud deployment
- Advanced agents / MCP
- Full UI
- Postgres / pgvector
- In-memory cache optimization
- Incremental reindexing
- Private GitHub repositories

## Milestones

### Milestone 9 — Portfolio Polish + v1 Closure (completed)

**Problem M9 solves:** The product works end-to-end; reviewers still need a clear public story—what it is, how to run it, how it is designed, and where it stops.

**Added:**

- README restructured as the public portfolio document
- Mermaid architecture diagram (GitHub as source adapter → shared pipeline)
- Design decisions / trade-offs, limitations, and future work separated
- `PORTFOLIO_NOTES.md` for interview pitch and CV bullets
- v1 status marked complete

**Out of scope for M9:** new API endpoints, backend features, UI, agents, cloud deployment.

### Milestone 8 — Demo / CLI Flow (completed)

**Problem the demo solves:** Portfolio reviewers need a one-command way to see the full product flow without assembling curl requests by hand.

**Why HTTP instead of internal services:** The script behaves like an external client, validates the real API contract, and stays decoupled from backend internals.

**Added:**

- `scripts/demo_github.py` (`--url`, `--question`, `--api-base-url`, `--top-k`, `--include-tests`)
- Step-by-step output: health → index-github → search → ask → list indexes
- Tests with mocked `httpx` (no live API / GitHub / OpenAI / Gemini)
- Character-length chunk safeguard (`MAX_CHARS_PER_CHUNK`) after OpenAI embedding limit discovery during manual testing

**Manual verification:** Completed with fake providers and OpenAI.

### Milestone 7 — GitHub Ingestion for Public Repositories (completed)

- `POST /repositories/index-github` for public `https://github.com/owner/repo` URLs
- `GitHubRepositoryIngestor` with `git clone --depth 1` via `subprocess.run` (no `shell=True`)
- URL validation; temporary clone cleanup; reuses `RepositoryIndexer` → `SQLiteIndexStore`
- `git` installed in Docker image
- Tests mock clone operations

### Milestone 6 — Docker + Developer Experience (completed)

- `Dockerfile`, `.dockerignore`, `docker-compose.yml`
- `./data` bind mount for SQLite; fake providers default in `.env.example`
- Docker for local reproducibility, not production deployment

### Milestone 5 — SQLite Persistence + Index Management (completed)

- `IndexStore` protocol + `SQLiteIndexStore`
- Index management endpoints; search/ask survive restart
- Tests use temporary SQLite files only

### Milestone 4 — RAG Answering with Citations (completed)

- `LLMProvider` + OpenAI / Gemini / fake
- `RAGAnswerService` + `POST /repositories/ask` with sources

### Milestone 3 — Embeddings + Semantic Search (completed)

- `EmbeddingProvider` + OpenAI / Gemini / fake
- `RepositoryIndexer`, `SemanticSearchService`
- `source_type`, `include_tests`, `MAX_CHUNKS_TO_EMBED`

### Milestone 2 — Content Extraction + Chunking (completed)

- `ContentExtractor`, `ChunkingService`, `POST /repositories/chunks`
- Skipped-file traceability; overlap validation

### Milestone 1 — Backend Foundation + Repository Scanner (completed)

- `GET /health`, `POST /repositories/scan`
- Layered structure; sensitive file exclusion; pytest foundation

## Tech Stack

- Python 3.11+
- FastAPI, Pydantic, uvicorn
- pytest, httpx
- SQLite
- Docker (local development only)
- OpenAI / Gemini SDKs (optional at runtime; fake providers for tests)

## Architecture Decisions

### Layered boundaries

| Layer | Responsibility |
| --- | --- |
| `api/routes` | HTTP only: request parsing, status codes, response mapping |
| `schemas` | Pydantic models for API input/output |
| `domain` | Internal dataclasses with no FastAPI dependency |
| `services` | Business logic (scanning, extraction, chunking, embeddings, search, RAG) |
| `utils` | Small reusable helpers |
| `core` | Shared config and domain errors |

### Design trade-offs (summary)

- **SQLite over vector DB** — local-first v1 without ops complexity
- **Python cosine similarity** — adequate for small indexes; pgvector deferred
- **Provider protocols** — OpenAI / Gemini / fake without rewriting indexer or RAG
- **Fake providers** — free demos and deterministic CI
- **GitHub as adapter** — one pipeline for local and remote sources
- **Docker for DX** — not production hosting
- **Char limit vs tokenizer** — protect embedding APIs without tiktoken in v1

### Scanner and safety

- Skips noise directories and sensitive files before content processing
- Binary detection and 1 MB size cap
- Cloned repos are untrusted; no code execution; no `shell=True`
- Errors raised in services, mapped to HTTP in routes

### Persistence and search

- `SQLITE_DB_PATH` is the single source of truth
- Services depend on `IndexStore`, not SQLite directly
- `created_at` uses timezone-aware UTC ISO timestamps
- For GitHub indexes, `repository_path` may be a temp clone path; `github_url` identifies the source

### Embedding / LLM

- Factories select providers via env
- Quota → `402`, rate limit → `429`
- `MAX_CHUNKS_TO_EMBED` and `MAX_CHARS_PER_CHUNK` checked before / during indexing

### RAG

- Search returns ranked chunks; ask synthesizes grounded answers
- Sources are metadata only (no chunk body in citations)
- Insufficient context returns a safe message without calling the LLM

## Learning Goals

- Recover Python fluency
- Practice clean backend structure
- Build confidence reading and reviewing AI-generated code

## Post-v1 Future Improvements

Optional ideas if the project is extended later. **Not required for portfolio v1.**

1. Private repository support and GitHub token / GitHub App auth
2. Branch selection, size limits, rate-limit handling
3. Incremental reindexing and optional clone cache
4. Postgres + pgvector or a dedicated vector DB
5. In-memory cache for hot indexes
6. Cloud deployment, secrets management, CI/CD
7. UI
8. Agents / MCP / tool calling

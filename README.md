# AI Repository Assistant

Backend service that scans local code repositories, chunks readable content, indexes embeddings in SQLite, and answers questions with RAG and citations.

## What it does

- Scan a local repository path and summarize files, languages, and ignored paths
- Extract readable source files and split them into overlapping chunks
- Index chunks with embeddings (OpenAI, Gemini, or fake providers for local dev)
- Search indexed content by semantic similarity
- Ask questions grounded in retrieved chunks with source citations
- Persist indexes in SQLite across API restarts

## Prerequisites

- Python 3.11+ (local setup)
- Docker and Docker Compose (optional, for containerized local dev)

## Quickstart (local, no Docker)

**Windows (PowerShell or cmd):**

```bash
git clone <repository-url>
cd ai-repository-assistant
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

**macOS / Linux:**

```bash
git clone <repository-url>
cd ai-repository-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API docs.

## Quickstart (Docker)

Docker is for **local development and reproducible execution**, not production deployment.

**Windows:**

```bash
copy .env.example .env
docker compose up --build
```

**macOS / Linux:**

```bash
cp .env.example .env
docker compose up --build
```

The API listens on `http://127.0.0.1:8000`.

### SQLite persistence in Docker

Your `.env` may set `SQLITE_DB_PATH=./data/ai_repository_assistant.db` for local runs. **Docker Compose intentionally overrides this** at runtime to `/app/data/ai_repository_assistant.db` inside the container.

The host persists that file through the bind mount `./data:/app/data`:

- **Inside the container:** `/app/data/ai_repository_assistant.db`
- **On your machine:** `./data/ai_repository_assistant.db`

Indexes survive `docker compose down` and container restarts **as long as you keep the local `./data` directory**. If you delete `./data`, persisted indexes are removed. The `data/` directory is gitignored — do not commit database files.

### Indexing a repository inside Docker

Repository paths in API requests must exist **inside the container**.

`docker-compose.yml` mounts a repository at `/workspace` in **read-only** mode via:

```yaml
${REPO_MOUNT_SOURCE:-.}:/workspace:ro
```

- **Default:** the current project directory (`.`) is mounted at `/workspace`.
- **Custom repository:**

  Bash / macOS / Linux:

  ```bash
  REPO_MOUNT_SOURCE=/path/to/repo docker compose up --build
  ```

  Windows PowerShell:

  ```powershell
  $env:REPO_MOUNT_SOURCE="D:/projects/my-repo"
  docker compose up --build
  ```

In all cases, index with:

```json
{ "path": "/workspace" }
```

## Environment variables

Copy `.env.example` to `.env`. Never commit `.env`.

| Variable | Default | Description |
| --- | --- | --- |
| `EMBEDDING_PROVIDER` | `openai` in code; `fake` in `.env.example` | `fake`, `openai`, or `gemini` |
| `LLM_PROVIDER` | `openai` in code; `fake` in `.env.example` | `fake`, `openai`, or `gemini` |
| `MAX_CHUNKS_TO_EMBED` | `50` | Safety cap before embedding API calls |
| `SQLITE_DB_PATH` | `./data/ai_repository_assistant.db` locally | SQLite file path; overridden to `/app/data/ai_repository_assistant.db` in Docker Compose |
| `OPENAI_API_KEY` | empty | Required when using OpenAI providers |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `OPENAI_CHAT_MODEL` | `gpt-4.1-mini` | OpenAI chat model |
| `GEMINI_API_KEY` | empty | Required when using Gemini providers |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Gemini embedding model |
| `GEMINI_CHAT_MODEL` | `gemini-2.0-flash` | Gemini chat model |

### Local development without paid API keys

`.env.example` defaults to fake providers (no API keys required):

```env
EMBEDDING_PROVIDER=fake
LLM_PROVIDER=fake
```

Copy `.env.example` to `.env` to use these defaults.

## Run the API

### Without Docker

```bash
uvicorn app.main:app --reload
```

### With Docker

```bash
docker compose up --build
```

Stop with `Ctrl+C` or `docker compose down`.

## Run tests

Tests run on the host with pytest. Docker is not required.

```bash
pytest
```

Tests use fake embedding and LLM providers and temporary SQLite databases. They never call OpenAI or Gemini and never touch `./data/ai_repository_assistant.db`.

## Manual demo flow

Use fake providers (`.env.example` defaults) for a free end-to-end check.

### 1. Start the API

Local: `uvicorn app.main:app --reload`

Docker: `docker compose up --build`

### 2. Health check

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{ "status": "ok" }
```

### 3. Index a repository

Replace `YOUR_REPO_PATH` or use `/workspace` when running in Docker.

**macOS / Linux (local path):**

```bash
curl -X POST http://127.0.0.1:8000/repositories/index -H "Content-Type: application/json" -d '{"path": "/path/to/your/repo"}'
```

**Windows (PowerShell, local path):**

```powershell
curl -X POST http://127.0.0.1:8000/repositories/index -H "Content-Type: application/json" -d '{\"path\": \"D:/projects/ai-repository-assistant\"}'
```

**Docker (any OS, repo mounted at `/workspace`):**

```bash
curl -X POST http://127.0.0.1:8000/repositories/index -H "Content-Type: application/json" -d '{"path": "/workspace"}'
```

Save the `index_id` from the response.

### 4. Search the index

```bash
curl -X POST http://127.0.0.1:8000/repositories/search -H "Content-Type: application/json" -d '{"index_id": "YOUR_INDEX_ID", "query": "Where is chunking implemented?", "top_k": 3, "include_tests": false}'
```

### 5. Ask a question

```bash
curl -X POST http://127.0.0.1:8000/repositories/ask -H "Content-Type: application/json" -d '{"index_id": "YOUR_INDEX_ID", "question": "Where is chunking implemented?", "top_k": 3, "include_tests": false}'
```

### 6. List indexes

```bash
curl http://127.0.0.1:8000/repositories/indexes
```

### 7. Verify persistence (optional)

Restart the API (or run `docker compose down` then `docker compose up --build`) and repeat search or ask with the same `index_id`. Results should still work as long as the local `./data` directory was not deleted.

## Docker manual verification

```bash
docker compose up --build
curl http://127.0.0.1:8000/health
```

Run the index → search → ask → list flow above with `{"path": "/workspace"}`. Restart the container and confirm the same `index_id` still works while `./data` remains on the host.

## GitHub ingestion (public repositories)

Index a **public** GitHub repository by URL. The app clones the repo into a temporary directory, runs the same scan → chunk → embed → persist pipeline as local indexing, then deletes the clone. The persisted artifact is the SQLite index, not the cloned repository.

**Scope:** public `https://github.com/owner/repo` URLs only. Private repos, OAuth, GitHub App, PRs, issues, and agents are out of scope.

**Requirements:** `git` must be installed on the host for local runs. The Docker image includes `git`.

### Index a GitHub repository

```bash
curl -X POST http://127.0.0.1:8000/repositories/index-github -H "Content-Type: application/json" -d '{"url": "https://github.com/owner/repo"}'
```

Response includes `source: "github"` and `github_url` in addition to the standard index fields.

### Search and ask after GitHub indexing

Use the returned `index_id` with the existing endpoints (unchanged):

```bash
curl -X POST http://127.0.0.1:8000/repositories/search -H "Content-Type: application/json" -d '{"index_id": "YOUR_INDEX_ID", "query": "How does authentication work?", "top_k": 3, "include_tests": false}'
```

```bash
curl -X POST http://127.0.0.1:8000/repositories/ask -H "Content-Type: application/json" -d '{"index_id": "YOUR_INDEX_ID", "question": "How does authentication work?", "top_k": 3, "include_tests": false}'
```

Cloned repositories are treated as untrusted input. Sensitive files (`.env`, keys, etc.) are still excluded during scanning. No code from the repository is executed.

## API endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Service health |
| `POST` | `/repositories/scan` | Scan repository metadata |
| `POST` | `/repositories/chunks` | Extract and chunk files |
| `POST` | `/repositories/index` | Index local repository chunks |
| `POST` | `/repositories/index-github` | Index public GitHub repository by URL |
| `POST` | `/repositories/search` | Semantic search |
| `POST` | `/repositories/ask` | RAG answer with citations |
| `GET` | `/repositories/indexes` | List persisted indexes |
| `GET` | `/repositories/indexes/{index_id}` | Get index metadata |
| `DELETE` | `/repositories/indexes/{index_id}` | Delete index and chunks |

Interactive docs: `http://127.0.0.1:8000/docs`

### Security: excluded secret files

The scanner skips sensitive files such as `.env`, `.env.local`, `*.pem`, `*.key`, `id_rsa`, `credentials.json`, and `secrets.json`. These files are never chunked or indexed.

### OpenAI billing / quota

If OpenAI quota is exceeded, `/repositories/index` returns `402` with a clear message. Use `EMBEDDING_PROVIDER=fake` for local development.

### Safety limit: `MAX_CHUNKS_TO_EMBED`

Default `50`. Repositories with more chunks return `400` before any embedding API call.

## Project structure

```
app/
  main.py
  api/routes/
  core/
  domain/
  services/
  schemas/
  utils/
tests/
Dockerfile
docker-compose.yml
```

## Milestones

- **M1:** FastAPI backend, repository scanner, file filtering
- **M2:** Content extraction, chunking, skipped-file traceability
- **M3:** Embedding providers, semantic search, `source_type`, `include_tests`
- **M4:** LLM providers, RAG answering with citations
- **M5:** SQLite persistence and index management
- **M6:** Docker and developer experience
- **M7:** GitHub ingestion for public repositories (this milestone)

## Next steps

See `PROJECT_NOTES.md` for architecture notes and future work.

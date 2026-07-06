# AI Repository Assistant

Backend service that scans local code repositories, chunks readable content, and supports semantic search over indexed chunks. Built as the foundation for future RAG and agent-based analysis.

## Milestone 1

- FastAPI backend with health check and repository scan endpoints
- Local filesystem scanning with ignored directories, sensitive file filtering, and binary/large file filtering

## Milestone 2

- Content extraction from scanned repository files
- Line-based chunking with overlap for future RAG indexing
- `POST /repositories/chunks` endpoint with skipped-file traceability

## Milestone 3

- OpenAI and Gemini embedding providers behind a shared abstraction
- In-memory vector store with cosine similarity search
- `POST /repositories/index` and `POST /repositories/search` endpoints
- `source_type` metadata and `include_tests` filtering

## Milestone 4

- `LLMProvider` abstraction with OpenAI, Gemini, and fake providers
- `RAGAnswerService` for retrieval + grounded answer generation
- `POST /repositories/ask` endpoint with citations

No agents, external vector DB, or GitHub integration yet.

## Requirements

- Python 3.11+
- Dependencies listed in `requirements.txt`

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Local development (no external API calls)

Use the fake embedding provider:

```env
EMBEDDING_PROVIDER=fake
LLM_PROVIDER=fake
MAX_CHUNKS_TO_EMBED=50
```

This lets you manually test `/repositories/index`, `/repositories/search`, and `/repositories/ask` without OpenAI or Gemini credentials.

### Production embedding providers

OpenAI (default):

```env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

For Gemini:

```env
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=your-key
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

For LLM answering with OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_CHAT_MODEL=gpt-4.1-mini
```

For Gemini chat:

```env
LLM_PROVIDER=gemini
GEMINI_CHAT_MODEL=gemini-2.0-flash
```

### OpenAI billing / quota

Indexing calls the embedding API once per chunk batch. If your OpenAI account has no billing or exceeded quota, `/repositories/index` returns `402` with a clear message instead of a raw server error.

Use `EMBEDDING_PROVIDER=fake` for local development, or ensure your OpenAI account has active billing before indexing real repositories.

### Safety limit: `MAX_CHUNKS_TO_EMBED`

Default: `50`. If a repository produces more chunks than this limit, indexing stops **before** any embedding API call and returns `400` with a clear error. Increase the limit only when you intentionally want to index larger repositories.

## Run the API

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive docs: `http://127.0.0.1:8000/docs`

## Endpoints

### `GET /health`

Returns service status.

```json
{ "status": "ok" }
```

### `POST /repositories/scan`

Scans a local repository path.

Request:

```json
{ "path": "D:/projects/my-repo" }
```

Response includes `repository_path`, `total_files`, `total_lines`, `languages`, `files`, `ignored_directories`, and `ignored_files`.

### Security: excluded secret files

The scanner intentionally skips sensitive files such as `.env`, `.env.local`, `*.pem`, `*.key`, `id_rsa`, `credentials.json`, and `secrets.json`. These files are never chunked or indexed.

**Never commit `.env` files to git.** Keep API keys out of repositories you scan in production.

### `POST /repositories/chunks`

Extracts readable file content and splits it into overlapping line-based chunks.

Request:

```json
{
  "path": "D:/projects/my-repo",
  "max_lines_per_chunk": 80,
  "overlap_lines": 10
}
```

Response includes `repository_path`, `total_files_processed`, `total_files_skipped`, `total_chunks`, `chunks`, and `skipped_files`.

### `POST /repositories/index`

Indexes repository chunks with embeddings for semantic search.

Request:

```json
{
  "path": "D:/projects/my-repo",
  "max_lines_per_chunk": 80,
  "overlap_lines": 10
}
```

Response includes `index_id`, `repository_path`, `total_chunks_indexed`, and `embedding_model`.

### `POST /repositories/search`

Searches an indexed repository by semantic similarity.

Request:

```json
{
  "index_id": "some-generated-id",
  "query": "Where is the chunking logic implemented?",
  "top_k": 5,
  "include_tests": false
}
```

Each result includes `source_type` (`source`, `test`, `docs`, `config`, or `other`). Set `include_tests` to `false` to exclude test files from results without changing similarity scoring.

Response includes `index_id`, `query`, `total_results`, and ranked `results`.

### `POST /repositories/ask`

Answers a question about an already indexed repository using retrieved chunks and an LLM.

Request:

```json
{
  "index_id": "some-generated-id",
  "question": "Where is the chunking logic implemented?",
  "top_k": 5,
  "include_tests": false
}
```

Response includes `answer` and `sources` (file path, line range, score, `source_type`). Requires a prior call to `/repositories/index`; it does not reindex.

## Run tests

```bash
pytest
```

Tests use fake embedding and LLM providers and never call OpenAI or Gemini.

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
```

## Next steps

See `PROJECT_NOTES.md` for milestone roadmap and technical decisions.

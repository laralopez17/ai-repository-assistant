# AI Repository Assistant

Backend service that scans local code repositories and returns structural metadata about files, extensions, and line counts. Built as the foundation for future RAG and agent-based analysis.

## Milestone 1

- FastAPI backend with health check and repository scan endpoints
- Local filesystem scanning with ignored directories and binary/large file filtering
- No AI, database, or GitHub integration yet

## Requirements

- Python 3.11+
- Dependencies listed in `requirements.txt`

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

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

Response includes `repository_path`, `total_files`, `total_lines`, `languages`, `files`, and `ignored_directories`.

## Run tests

```bash
pytest
```

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

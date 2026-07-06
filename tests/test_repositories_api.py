from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.errors import EmbeddingProviderError
from app.main import app
from app.services.embedding_factory import get_embedding_provider

client = TestClient(app)


class QuotaFailingEmbeddingProvider:
    model_name = "test-model"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingProviderError(
            "OpenAI quota or billing limit exceeded. Check your OpenAI account billing settings.",
            status_code=402,
        )

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


def test_scan_repository_endpoint(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")

    response = client.post("/repositories/scan", json={"path": str(repo)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_files"] == 1
    assert payload["total_lines"] == 1
    assert payload["files"][0]["relative_path"] == "app.py"


def test_scan_repository_reports_ignored_secret_files(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    (repo / ".env").write_text("OPENAI_API_KEY=super-secret\n", encoding="utf-8")

    response = client.post("/repositories/scan", json={"path": str(repo)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_files"] == 1
    assert ".env" in payload["ignored_files"]


def test_scan_repository_returns_404_when_path_missing():
    response = client.post(
        "/repositories/scan",
        json={"path": "/definitely/missing/path"},
    )

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_scan_repository_returns_400_when_path_is_file(tmp_path: Path):
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("hello", encoding="utf-8")

    response = client.post("/repositories/scan", json={"path": str(file_path)})

    assert response.status_code == 400
    assert "not a directory" in response.json()["detail"]


def test_chunk_repository_endpoint(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    response = client.post(
        "/repositories/chunks",
        json={"path": str(repo)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_files_processed"] == 1
    assert payload["total_files_skipped"] == 0
    assert payload["total_chunks"] == 1
    assert payload["chunks"][0]["file_path"] == "app.py"
    assert payload["chunks"][0]["chunk_id"] == "app.py::chunk-000"
    assert payload["chunks"][0]["start_line"] == 1
    assert payload["chunks"][0]["end_line"] == 3
    assert payload["chunks"][0]["content"] == "alpha\nbeta\ngamma"
    assert payload["skipped_files"] == []


def test_chunk_repository_skips_unreadable_files(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "good.txt").write_text("ok\n", encoding="utf-8")
    (repo / "bad.txt").write_bytes(b"\xff\xfe\xfd")

    response = client.post(
        "/repositories/chunks",
        json={"path": str(repo)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_files_processed"] == 1
    assert payload["total_files_skipped"] == 1
    assert payload["total_chunks"] == 1
    assert payload["skipped_files"][0]["file_path"] == "bad.txt"
    assert payload["skipped_files"][0]["reason"] == "cannot decode as utf-8"


def test_chunk_repository_returns_422_for_invalid_overlap(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")

    response = client.post(
        "/repositories/chunks",
        json={
            "path": str(repo),
            "max_lines_per_chunk": 80,
            "overlap_lines": 80,
        },
    )

    assert response.status_code == 422


def test_chunk_repository_skips_secret_files(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("safe content\n", encoding="utf-8")
    (repo / ".env").write_text("OPENAI_API_KEY=super-secret\n", encoding="utf-8")
    (repo / "server.pem").write_text("-----BEGIN CERT-----\n", encoding="utf-8")

    response = client.post("/repositories/chunks", json={"path": str(repo)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_files_processed"] == 1
    assert payload["total_chunks"] == 1
    assert payload["chunks"][0]["file_path"] == "app.py"
    assert all(".env" not in chunk["content"] for chunk in payload["chunks"])
    assert all("super-secret" not in chunk["content"] for chunk in payload["chunks"])


def test_index_repository_skips_secret_files(
    api_client: TestClient,
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("chunk logic here\n", encoding="utf-8")
    (repo / ".env").write_text("OPENAI_API_KEY=super-secret\n", encoding="utf-8")

    index_response = api_client.post("/repositories/index", json={"path": str(repo)})
    assert index_response.status_code == 200
    assert index_response.json()["total_chunks_indexed"] == 1

    index_id = index_response.json()["index_id"]
    search_response = api_client.post(
        "/repositories/search",
        json={
            "index_id": index_id,
            "query": "super-secret OPENAI_API_KEY",
            "top_k": 5,
        },
    )

    assert search_response.status_code == 200
    payload = search_response.json()
    assert all("super-secret" not in result["content"] for result in payload["results"])
    assert all(".env" not in result["file_path"] for result in payload["results"])


def test_index_repository_returns_provider_error_without_500(
    api_client: TestClient,
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("chunk logic\n", encoding="utf-8")

    app.dependency_overrides[get_embedding_provider] = (
        lambda: QuotaFailingEmbeddingProvider()
    )
    try:
        response = api_client.post("/repositories/index", json={"path": str(repo)})
    finally:
        app.dependency_overrides.pop(get_embedding_provider, None)

    assert response.status_code == 402
    assert response.status_code != 500
    assert "quota or billing" in response.json()["detail"].lower()


def test_index_repository_returns_400_when_chunk_limit_exceeded(
    api_client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.core.config.MAX_CHUNKS_TO_EMBED", 1)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "one.py").write_text("chunk one\n", encoding="utf-8")
    (repo / "two.py").write_text("chunk two\n", encoding="utf-8")

    response = api_client.post("/repositories/index", json={"path": str(repo)})

    assert response.status_code == 400
    assert "exceeding the limit of 1" in response.json()["detail"]


def test_index_repository_endpoint(api_client: TestClient, tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    app_dir = repo / "app"
    app_dir.mkdir()
    (app_dir / "chunking.py").write_text("chunk logic here\n", encoding="utf-8")
    (app_dir / "scanner.py").write_text("scanner logic here\n", encoding="utf-8")

    response = api_client.post("/repositories/index", json={"path": str(repo)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_chunks_indexed"] == 2
    assert payload["embedding_model"] == "fake-embedding-model"
    assert payload["repository_path"] == str(repo.resolve())
    assert payload["index_id"]


def test_search_repository_endpoint(api_client: TestClient, tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    app_dir = repo / "app"
    app_dir.mkdir()
    (app_dir / "chunking.py").write_text("chunk logic here\n", encoding="utf-8")
    (app_dir / "scanner.py").write_text("scanner logic here\n", encoding="utf-8")

    index_response = api_client.post("/repositories/index", json={"path": str(repo)})
    index_id = index_response.json()["index_id"]

    search_response = api_client.post(
        "/repositories/search",
        json={
            "index_id": index_id,
            "query": "Where is the chunking logic implemented?",
            "top_k": 1,
        },
    )

    assert search_response.status_code == 200
    payload = search_response.json()
    assert payload["total_results"] == 1
    assert payload["results"][0]["file_path"] == "app/chunking.py"
    assert payload["results"][0]["score"] == 1.0
    assert payload["results"][0]["source_type"] == "source"


def test_search_repository_excludes_tests_when_requested(
    api_client: TestClient,
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    app_dir = repo / "app"
    tests_dir = repo / "tests"
    app_dir.mkdir()
    tests_dir.mkdir()
    (app_dir / "chunking.py").write_text("chunk logic here\n", encoding="utf-8")
    (tests_dir / "test_chunking.py").write_text("chunk logic here\n", encoding="utf-8")

    index_id = api_client.post(
        "/repositories/index",
        json={"path": str(repo)},
    ).json()["index_id"]

    response = api_client.post(
        "/repositories/search",
        json={
            "index_id": index_id,
            "query": "Where is the chunking logic implemented?",
            "top_k": 1,
            "include_tests": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_results"] == 1
    assert payload["results"][0]["source_type"] == "source"
    assert payload["results"][0]["file_path"] == "app/chunking.py"


def test_search_repository_returns_404_for_missing_index(api_client: TestClient):
    response = api_client.post(
        "/repositories/search",
        json={
            "index_id": "missing-index-id",
            "query": "chunking logic",
            "top_k": 1,
        },
    )

    assert response.status_code == 404
    assert "Index not found" in response.json()["detail"]


def test_search_repository_returns_422_for_invalid_top_k(
    api_client: TestClient,
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("chunk logic\n", encoding="utf-8")
    index_id = api_client.post(
        "/repositories/index",
        json={"path": str(repo)},
    ).json()["index_id"]

    response = api_client.post(
        "/repositories/search",
        json={
            "index_id": index_id,
            "query": "chunk",
            "top_k": 0,
        },
    )

    assert response.status_code == 422


def test_ask_repository_endpoint(api_client: TestClient, tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    app_dir = repo / "app"
    tests_dir = repo / "tests"
    app_dir.mkdir()
    tests_dir.mkdir()
    (app_dir / "chunking.py").write_text("chunk logic here\n", encoding="utf-8")
    (tests_dir / "test_chunking.py").write_text("chunk logic here\n", encoding="utf-8")

    index_id = api_client.post(
        "/repositories/index",
        json={"path": str(repo)},
    ).json()["index_id"]

    response = api_client.post(
        "/repositories/ask",
        json={
            "index_id": index_id,
            "question": "Where is the chunking logic implemented?",
            "top_k": 1,
            "include_tests": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["index_id"] == index_id
    assert "app/chunking.py" in payload["answer"]
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["source_type"] == "source"
    assert payload["sources"][0]["file_path"] == "app/chunking.py"


def test_ask_repository_excludes_test_sources(api_client: TestClient, tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    app_dir = repo / "app"
    tests_dir = repo / "tests"
    app_dir.mkdir()
    tests_dir.mkdir()
    (app_dir / "chunking.py").write_text("chunk logic here\n", encoding="utf-8")
    (tests_dir / "test_chunking.py").write_text("chunk logic here\n", encoding="utf-8")

    index_id = api_client.post(
        "/repositories/index",
        json={"path": str(repo)},
    ).json()["index_id"]

    response = api_client.post(
        "/repositories/ask",
        json={
            "index_id": index_id,
            "question": "Where is the chunking logic implemented?",
            "top_k": 5,
            "include_tests": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert all(source["source_type"] != "test" for source in payload["sources"])


def test_ask_repository_returns_insufficient_context_without_sources(
    api_client: TestClient,
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_chunking.py").write_text("chunk logic here\n", encoding="utf-8")

    index_id = api_client.post(
        "/repositories/index",
        json={"path": str(repo)},
    ).json()["index_id"]

    response = api_client.post(
        "/repositories/ask",
        json={
            "index_id": index_id,
            "question": "Where is the chunking logic implemented?",
            "top_k": 1,
            "include_tests": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "not enough context" in payload["answer"].lower()
    assert payload["sources"] == []


def test_ask_repository_returns_404_for_missing_index(api_client: TestClient):
    response = api_client.post(
        "/repositories/ask",
        json={
            "index_id": "missing-index-id",
            "question": "Where is the chunking logic implemented?",
            "top_k": 1,
        },
    )

    assert response.status_code == 404
    assert "Index not found" in response.json()["detail"]


def test_ask_repository_returns_422_for_empty_question(
    api_client: TestClient,
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("chunk logic\n", encoding="utf-8")
    index_id = api_client.post(
        "/repositories/index",
        json={"path": str(repo)},
    ).json()["index_id"]

    response = api_client.post(
        "/repositories/ask",
        json={
            "index_id": index_id,
            "question": "",
            "top_k": 1,
        },
    )

    assert response.status_code == 422

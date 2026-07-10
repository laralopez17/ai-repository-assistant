import ast
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from scripts.demo_github import (
    DemoError,
    ask_repository,
    check_health,
    index_github,
    list_indexes,
    main,
    parse_args,
    run_demo,
    search_repository,
)

DEMO_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "demo_github.py"
FORBIDDEN_IMPORT_PREFIXES = (
    "app.services",
    "app.domain",
    "app.core",
    "app.api",
)


def test_demo_script_does_not_import_internal_services():
    tree = ast.parse(DEMO_SCRIPT.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    for module_name in imported:
        assert not module_name.startswith(FORBIDDEN_IMPORT_PREFIXES), module_name


def test_parse_args_requires_url_and_question():
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_defaults():
    args = parse_args(
        [
            "--url",
            "https://github.com/owner/repo",
            "--question",
            "What does this project do?",
        ]
    )
    assert args.url == "https://github.com/owner/repo"
    assert args.question == "What does this project do?"
    assert args.api_base_url == "http://127.0.0.1:8000"
    assert args.top_k == 5
    assert args.include_tests is False


def test_parse_args_custom_options():
    args = parse_args(
        [
            "--url",
            "https://github.com/owner/repo",
            "--question",
            "Where is auth?",
            "--api-base-url",
            "http://localhost:9000",
            "--top-k",
            "3",
            "--include-tests",
        ]
    )
    assert args.api_base_url == "http://localhost:9000"
    assert args.top_k == 3
    assert args.include_tests is True


def _mock_response(status_code: int, payload: dict | None = None, text: str = "") -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.content = b"{}" if payload is not None else (text.encode() if text else b"")
    response.text = text
    response.json.return_value = payload if payload is not None else {}
    return response


def test_check_health_success():
    client = MagicMock(spec=httpx.Client)
    client.base_url = "http://127.0.0.1:8000"
    client.request.return_value = _mock_response(200, {"status": "ok"})

    assert check_health(client) == {"status": "ok"}


def test_check_health_api_unreachable():
    client = MagicMock(spec=httpx.Client)
    client.base_url = "http://127.0.0.1:8000"
    client.request.side_effect = httpx.ConnectError("connection refused")

    with pytest.raises(DemoError, match="Could not reach API"):
        check_health(client)


def test_index_github_maps_api_error():
    client = MagicMock(spec=httpx.Client)
    client.base_url = "http://127.0.0.1:8000"
    client.request.return_value = _mock_response(
        400,
        {"detail": "Only github.com repository URLs are supported"},
    )

    with pytest.raises(DemoError, match="GitHub ingestion failed"):
        index_github(client, "https://gitlab.com/owner/repo")


def test_search_and_ask_error_messages():
    client = MagicMock(spec=httpx.Client)
    client.base_url = "http://127.0.0.1:8000"
    client.request.return_value = _mock_response(404, {"detail": "Index not found"})

    with pytest.raises(DemoError, match="Semantic search failed"):
        search_repository(client, "missing", "query", 5, False)

    with pytest.raises(DemoError, match="RAG answer failed"):
        ask_repository(client, "missing", "question", 5, False)


def test_run_demo_success_flow(capsys):
    client = MagicMock(spec=httpx.Client)
    client.base_url = "http://127.0.0.1:8000"

    responses = [
        _mock_response(200, {"status": "ok"}),
        _mock_response(
            200,
            {
                "index_id": "idx-1",
                "repository_path": "/tmp/repo",
                "total_chunks_indexed": 12,
                "embedding_model": "fake-embedding-model",
                "source": "github",
                "github_url": "https://github.com/owner/repo",
            },
        ),
        _mock_response(
            200,
            {
                "index_id": "idx-1",
                "query": "What does this project do?",
                "total_results": 1,
                "results": [
                    {
                        "chunk_id": "a::chunk-000",
                        "file_path": "app/main.py",
                        "start_line": 1,
                        "end_line": 10,
                        "score": 0.91,
                        "content": "ignored",
                        "source_type": "source",
                    }
                ],
            },
        ),
        _mock_response(
            200,
            {
                "index_id": "idx-1",
                "question": "What does this project do?",
                "answer": "It recommends books.",
                "sources": [
                    {
                        "chunk_id": "a::chunk-000",
                        "file_path": "app/main.py",
                        "start_line": 1,
                        "end_line": 10,
                        "score": 0.91,
                        "source_type": "source",
                    }
                ],
            },
        ),
        _mock_response(
            200,
            {
                "indexes": [
                    {
                        "index_id": "idx-1",
                        "repository_path": "/tmp/repo",
                        "embedding_model": "fake-embedding-model",
                        "total_chunks_indexed": 12,
                        "created_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
        ),
    ]
    client.request.side_effect = responses

    exit_code = run_demo(
        client,
        url="https://github.com/owner/repo",
        question="What does this project do?",
        top_k=3,
        include_tests=False,
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "idx-1" in output
    assert "fake-embedding-model" in output
    assert "app/main.py" in output
    assert "It recommends books." in output
    assert client.request.call_count == 5


def test_main_returns_1_when_api_unreachable(monkeypatch, capsys):
    def fake_client(*args, **kwargs):
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.base_url = "http://127.0.0.1:8000"
        client.request.side_effect = httpx.ConnectError("connection refused")
        return client

    monkeypatch.setattr("scripts.demo_github.httpx.Client", fake_client)

    exit_code = main(
        [
            "--url",
            "https://github.com/owner/repo",
            "--question",
            "What does this do?",
        ]
    )

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "Could not reach API" in err


def test_list_indexes_success():
    client = MagicMock(spec=httpx.Client)
    client.base_url = "http://127.0.0.1:8000"
    client.request.return_value = _mock_response(200, {"indexes": []})

    assert list_indexes(client) == {"indexes": []}

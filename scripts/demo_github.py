#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TOP_K = 5
REQUEST_TIMEOUT_SECONDS = 120.0


class DemoError(Exception):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Demo the AI Repository Assistant GitHub flow: "
            "index a public repo, search, and ask a question via the HTTP API."
        )
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Public GitHub repository URL (https://github.com/owner/repo)",
    )
    parser.add_argument(
        "--question",
        required=True,
        help="Question to ask about the indexed repository",
    )
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help=f"API base URL (default: {DEFAULT_API_BASE_URL})",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Number of search/ask results (default: {DEFAULT_TOP_K})",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test files in search and ask results",
    )
    return parser.parse_args(argv)


def _api_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"
    detail = payload.get("detail", payload)
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    return str(detail)


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> Any:
    try:
        response = client.request(method, path, json=json_body)
    except httpx.ConnectError as error:
        raise DemoError(
            f"Could not reach API at {client.base_url}. Is the server running?"
        ) from error
    except httpx.TimeoutException as error:
        raise DemoError(
            f"Request to {client.base_url}{path} timed out."
        ) from error
    except httpx.HTTPError as error:
        raise DemoError(f"HTTP request failed: {error}") from error

    if response.status_code >= 400:
        raise DemoError(_api_error_detail(response))
    if response.status_code == 204 or not response.content:
        return None
    return response.json()


def check_health(client: httpx.Client) -> dict[str, Any]:
    try:
        payload = _request(client, "GET", "/health")
    except DemoError as error:
        if "Could not reach API" in str(error):
            raise
        raise DemoError("API health check failed.") from error
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise DemoError("API health check failed.")
    return payload


def index_github(client: httpx.Client, url: str) -> dict[str, Any]:
    try:
        return _request(client, "POST", "/repositories/index-github", json_body={"url": url})
    except DemoError as error:
        if "Could not reach API" in str(error) or "timed out" in str(error):
            raise
        raise DemoError(f"GitHub ingestion failed: {error}") from error


def search_repository(
    client: httpx.Client,
    index_id: str,
    query: str,
    top_k: int,
    include_tests: bool,
) -> dict[str, Any]:
    try:
        return _request(
            client,
            "POST",
            "/repositories/search",
            json_body={
                "index_id": index_id,
                "query": query,
                "top_k": top_k,
                "include_tests": include_tests,
            },
        )
    except DemoError as error:
        if "Could not reach API" in str(error) or "timed out" in str(error):
            raise
        raise DemoError(f"Semantic search failed: {error}") from error


def ask_repository(
    client: httpx.Client,
    index_id: str,
    question: str,
    top_k: int,
    include_tests: bool,
) -> dict[str, Any]:
    try:
        return _request(
            client,
            "POST",
            "/repositories/ask",
            json_body={
                "index_id": index_id,
                "question": question,
                "top_k": top_k,
                "include_tests": include_tests,
            },
        )
    except DemoError as error:
        if "Could not reach API" in str(error) or "timed out" in str(error):
            raise
        raise DemoError(f"RAG answer failed: {error}") from error


def list_indexes(client: httpx.Client) -> dict[str, Any]:
    try:
        return _request(client, "GET", "/repositories/indexes")
    except DemoError as error:
        if "Could not reach API" in str(error) or "timed out" in str(error):
            raise
        raise DemoError(f"Failed to list indexes: {error}") from error


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def _print_search_results(results: list[dict[str, Any]]) -> None:
    if not results:
        print("  (no results)")
        return
    for index, result in enumerate(results, start=1):
        file_path = result.get("file_path", "?")
        score = result.get("score", "?")
        source_type = result.get("source_type", "?")
        start_line = result.get("start_line", "?")
        end_line = result.get("end_line", "?")
        print(f"  {index}. {file_path}")
        print(f"     score={score}  source_type={source_type}  lines={start_line}-{end_line}")


def _print_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        print("  (no sources)")
        return
    for index, source in enumerate(sources, start=1):
        file_path = source.get("file_path", "?")
        score = source.get("score", "?")
        source_type = source.get("source_type", "?")
        start_line = source.get("start_line", "?")
        end_line = source.get("end_line", "?")
        print(f"  {index}. {file_path}  score={score}  type={source_type}  lines={start_line}-{end_line}")


def run_demo(
    client: httpx.Client,
    *,
    url: str,
    question: str,
    top_k: int,
    include_tests: bool,
) -> int:
    api_base = str(client.base_url).rstrip("/")

    _print_header("AI Repository Assistant — GitHub Demo")
    print(f"API base URL : {api_base}")
    print(f"GitHub URL   : {url}")
    print(f"Question     : {question}")
    print(f"top_k        : {top_k}")
    print(f"include_tests: {include_tests}")

    print("\n[1/5] Checking API health...")
    check_health(client)
    print("  OK")

    print("\n[2/5] Indexing GitHub repository...")
    index_payload = index_github(client, url)
    index_id = index_payload["index_id"]
    print(f"  index_id             : {index_id}")
    print(f"  total_chunks_indexed : {index_payload.get('total_chunks_indexed')}")
    print(f"  embedding_model      : {index_payload.get('embedding_model')}")
    print(f"  source               : {index_payload.get('source')}")
    print(f"  github_url           : {index_payload.get('github_url')}")

    print("\n[3/5] Running semantic search...")
    search_payload = search_repository(
        client,
        index_id,
        question,
        top_k,
        include_tests,
    )
    print(f"  query          : {search_payload.get('query')}")
    print(f"  total_results  : {search_payload.get('total_results')}")
    print("  Top chunks:")
    _print_search_results(search_payload.get("results") or [])

    print("\n[4/5] Asking RAG question...")
    ask_payload = ask_repository(
        client,
        index_id,
        question,
        top_k,
        include_tests,
    )
    print("  Answer:")
    print(f"  {ask_payload.get('answer')}")
    print("  Sources:")
    _print_sources(ask_payload.get("sources") or [])

    print("\n[5/5] Listing persisted indexes...")
    indexes_payload = list_indexes(client)
    indexes = indexes_payload.get("indexes") or []
    print(f"  total indexes: {len(indexes)}")
    for item in indexes:
        print(
            f"  - {item.get('index_id')}  "
            f"chunks={item.get('total_chunks_indexed')}  "
            f"model={item.get('embedding_model')}"
        )

    _print_header("Demo complete")
    print(f"Persisted index_id: {index_id}")
    print("You can reuse this index_id with /repositories/search and /repositories/ask.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.top_k < 1:
        print("error: --top-k must be >= 1", file=sys.stderr)
        return 2

    base_url = args.api_base_url.rstrip("/")
    try:
        with httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT_SECONDS) as client:
            return run_demo(
                client,
                url=args.url,
                question=args.question,
                top_k=args.top_k,
                include_tests=args.include_tests,
            )
    except DemoError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

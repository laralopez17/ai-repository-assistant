from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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

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

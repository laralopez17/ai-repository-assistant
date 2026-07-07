import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS indexes (
    index_id TEXT PRIMARY KEY,
    repository_path TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    total_chunks_indexed INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    index_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    extension TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    content TEXT NOT NULL,
    source_type TEXT NOT NULL,
    embedding_json TEXT NOT NULL,
    FOREIGN KEY (index_id) REFERENCES indexes(index_id) ON DELETE CASCADE,
    UNIQUE (index_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_chunks_index_id ON chunks(index_id);
"""


def init_database(db_path: Path | str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.executescript(SCHEMA)
        connection.commit()


def connect(db_path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

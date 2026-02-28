"""SQLite storage for raw docs, processed docs, extractions, and reports."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DB_PATH: Path | None = None


def set_db_path(path: str | Path) -> None:
    global _DB_PATH
    _DB_PATH = Path(path)


def get_db_path() -> Path:
    if _DB_PATH is not None:
        return _DB_PATH
    base = Path(__file__).resolve().parent.parent
    return base / "data" / "intelligence.db"


def get_connection() -> sqlite3.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS raw_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            body TEXT,
            source_type TEXT NOT NULL,
            published_at TEXT,
            fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS processed_docs (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT,
            body TEXT,
            source_type TEXT NOT NULL,
            source_tier INTEGER NOT NULL,
            published_at TEXT,
            fetched_at TEXT NOT NULL,
            FOREIGN KEY (id) REFERENCES raw_docs(id)
        );

        CREATE TABLE IF NOT EXISTS extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER NOT NULL,
            entities_json TEXT,
            events_json TEXT,
            signal_tags_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES raw_docs(id)
        );

        CREATE TABLE IF NOT EXISTS contradictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            focus TEXT,
            doc_id_a INTEGER NOT NULL,
            doc_id_b INTEGER NOT NULL,
            snippet_a TEXT,
            snippet_b TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doc_id_a) REFERENCES raw_docs(id),
            FOREIGN KEY (doc_id_b) REFERENCES raw_docs(id)
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_json TEXT NOT NULL,
            report_md TEXT,
            confidence REAL,
            generated_at TEXT NOT NULL
        );
    """)
    conn.commit()


def insert_raw_doc(
    conn: sqlite3.Connection,
    url: str,
    title: str,
    body: str,
    source_type: str,
    published_at: str | None = None,
) -> int:
    fetched_at = datetime.utcnow().isoformat() + "Z"
    cur = conn.execute(
        "INSERT OR IGNORE INTO raw_docs (url, title, body, source_type, published_at, fetched_at) VALUES (?, ?, ?, ?, ?, ?)",
        (url, title, body, source_type, published_at or fetched_at, fetched_at),
    )
    conn.commit()
    if cur.lastrowid and cur.lastrowid > 0:
        return cur.lastrowid
    cur = conn.execute("SELECT id FROM raw_docs WHERE url = ?", (url,))
    row = cur.fetchone()
    return row["id"] if row else 0


def get_raw_docs(conn: sqlite3.Connection, limit: int | None = None) -> list[dict[str, Any]]:
    sql = "SELECT id, url, title, body, source_type, published_at, fetched_at FROM raw_docs ORDER BY id"
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def insert_processed_doc(
    conn: sqlite3.Connection,
    doc_id: int,
    url: str,
    title: str,
    body: str,
    source_type: str,
    source_tier: int,
    published_at: str | None,
    fetched_at: str,
) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO processed_docs (id, url, title, body, source_type, source_tier, published_at, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (doc_id, url, title, body, source_type, source_tier, published_at or "", fetched_at),
    )
    conn.commit()


def get_processed_docs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, url, title, body, source_type, source_tier, published_at, fetched_at FROM processed_docs ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]


def insert_extraction(
    conn: sqlite3.Connection,
    doc_id: int,
    entities: list[Any],
    events: list[Any],
    signal_tags: list[str],
) -> int:
    created_at = datetime.utcnow().isoformat() + "Z"
    cur = conn.execute(
        """INSERT INTO extractions (doc_id, entities_json, events_json, signal_tags_json, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (doc_id, json.dumps(entities), json.dumps(events), json.dumps(signal_tags), created_at),
    )
    conn.commit()
    return cur.lastrowid or 0


def get_extractions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, doc_id, entities_json, events_json, signal_tags_json, created_at FROM extractions ORDER BY doc_id"
    ).fetchall()
    return [
        {
            "id": r["id"], "doc_id": r["doc_id"], "created_at": r["created_at"],
            "entities": json.loads(r["entities_json"] or "[]"),
            "events": json.loads(r["events_json"] or "[]"),
            "signal_tags": json.loads(r["signal_tags_json"] or "[]"),
        }
        for r in rows
    ]


def insert_contradiction(
    conn: sqlite3.Connection,
    focus: str,
    doc_id_a: int,
    doc_id_b: int,
    snippet_a: str,
    snippet_b: str,
) -> int:
    created_at = datetime.utcnow().isoformat() + "Z"
    cur = conn.execute(
        """INSERT INTO contradictions (focus, doc_id_a, doc_id_b, snippet_a, snippet_b, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (focus, doc_id_a, doc_id_b, snippet_a, snippet_b, created_at),
    )
    conn.commit()
    return cur.lastrowid or 0


def get_contradictions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, focus, doc_id_a, doc_id_b, snippet_a, snippet_b, created_at FROM contradictions ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]


def insert_report(
    conn: sqlite3.Connection,
    report_json: dict[str, Any],
    report_md: str,
    confidence: float,
) -> int:
    generated_at = datetime.utcnow().isoformat() + "Z"
    cur = conn.execute(
        "INSERT INTO reports (report_json, report_md, confidence, generated_at) VALUES (?, ?, ?, ?)",
        (json.dumps(report_json), report_md, confidence, generated_at),
    )
    conn.commit()
    return cur.lastrowid or 0


def get_latest_report(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, report_json, report_md, confidence, generated_at FROM reports ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "report_json": json.loads(row["report_json"]),
        "report_md": row["report_md"],
        "confidence": row["confidence"],
        "generated_at": row["generated_at"],
    }

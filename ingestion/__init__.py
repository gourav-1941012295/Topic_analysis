"""Ingestion: fetch from sources and store raw docs."""

from .pipeline import run_ingestion
from .storage import (
    get_connection,
    get_db_path,
    get_processed_docs,
    get_raw_docs,
    init_schema,
    insert_raw_doc,
    set_db_path,
)

__all__ = [
    "run_ingestion",
    "get_connection",
    "get_db_path",
    "get_processed_docs",
    "get_raw_docs",
    "init_schema",
    "insert_raw_doc",
    "set_db_path",
]

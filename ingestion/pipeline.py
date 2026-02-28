"""Fetch from configured sources and store in raw_docs."""

import logging
from ingestion.storage import get_connection, init_schema, insert_raw_doc
from ingestion.sources.hn import fetch_hn
from ingestion.sources.rss import fetch_rss_feeds
from ingestion.sources.news_api import fetch_news_api
from config import get_sources, get_topic_name

logger = logging.getLogger(__name__)
TOPIC_WORD = lambda: (get_topic_name() or "").split()[0] or None


def _ingest_from(conn, items, max_docs: int | None, inserted: int) -> int:
    """Insert items into raw_docs; return new inserted count."""
    for item in items:
        if max_docs and inserted >= max_docs:
            break
        doc_id = insert_raw_doc(
            conn, item["url"], item["title"], item["body"],
            item["source_type"], item.get("published_at"),
        )
        if doc_id:
            inserted += 1
    return inserted


def run_ingestion(max_docs: int | None = None) -> int:
    """Fetch from config sources → raw_docs. Returns total inserted."""
    conn = get_connection()
    init_schema(conn)
    sources = get_sources()
    topic = get_topic_name()
    q = TOPIC_WORD()
    inserted = 0

    if sources.get("hn"):
        inserted = _ingest_from(conn, fetch_hn(limit=25, query=q), max_docs, inserted)
    inserted = _ingest_from(
        conn, fetch_rss_feeds(sources.get("rss_feeds") or [], limit_per_feed=10, query=q), max_docs, inserted
    )
    if sources.get("news_api"):
        inserted = _ingest_from(conn, fetch_news_api(topic or "AI", limit=20), max_docs, inserted)

    conn.close()
    logger.info("Ingestion done: %s docs", inserted)
    return inserted

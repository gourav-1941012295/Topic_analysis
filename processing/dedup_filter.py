"""Deduplicate by URL and filter by recency and source tier."""

import logging
from datetime import datetime, timedelta, timezone

from ingestion.storage import get_connection, get_raw_docs, init_schema, insert_processed_doc
from config import get_time_window_days

logger = logging.getLogger(__name__)

# official=3, news=2, rss=2, forum=1
SOURCE_TIER = {"news_api": 2, "rss": 2, "hn": 1, "reddit": 1}


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def run_dedup_and_filter() -> int:
    """
    Read raw_docs, dedupe by URL (already enforced in raw_docs), filter by time window,
    assign source_tier, write to processed_docs. Returns count of processed docs.
    """
    conn = get_connection()
    init_schema(conn)
    raw = get_raw_docs(conn)
    window_days = get_time_window_days()
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    count = 0
    for row in raw:
        published = _parse_date(row.get("published_at") or row.get("fetched_at"))
        if published and published.replace(tzinfo=timezone.utc) < cutoff:
            continue
        tier = SOURCE_TIER.get(row["source_type"], 1)
        insert_processed_doc(
            conn,
            doc_id=row["id"],
            url=row["url"],
            title=row["title"] or "",
            body=(row["body"] or "")[:100000],
            source_type=row["source_type"],
            source_tier=tier,
            published_at=row.get("published_at"),
            fetched_at=row["fetched_at"],
        )
        count += 1
    conn.close()
    logger.info("Dedup & filter: %s docs in processed_docs", count)
    return count

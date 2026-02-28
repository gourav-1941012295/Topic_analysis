"""RSS feed fetcher."""

import logging
from typing import Iterator
import feedparser
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _parse_date(entry: dict) -> str | None:
    for key in ("published_parsed", "updated_parsed"):
        p = entry.get(key)
        if p:
            try:
                dt = datetime(*p[:6], tzinfo=timezone.utc)
                return dt.isoformat().replace("+00:00", "Z")
            except Exception:
                pass
    return None


def fetch_rss_feeds(
    feeds: list[str],
    limit_per_feed: int = 15,
    query: str | None = None,
) -> Iterator[dict]:
    """
    Yield entries from RSS feeds. Each item: url, title, body, source_type, published_at.
    source_type is "rss". If query is set, filter by title/summary.
    """
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as e:
            logger.warning("RSS fetch %s failed: %s", feed_url, e)
            continue
        count = 0
        for entry in parsed.entries:
            if limit_per_feed and count >= limit_per_feed:
                break
            title = entry.get("title") or ""
            link = entry.get("link") or ""
            summary = entry.get("summary", "") or ""
            body = (title + "\n\n" + summary)[:50000]
            text = (title + " " + summary).lower()
            if query and query.lower() not in text:
                continue
            published_at = _parse_date(entry)
            count += 1
            yield {
                "url": link,
                "title": title,
                "body": body,
                "source_type": "rss",
                "published_at": published_at,
            }

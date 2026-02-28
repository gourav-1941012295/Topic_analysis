"""Hacker News API fetcher."""

import logging
from typing import Iterator
import requests

logger = logging.getLogger(__name__)

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


def fetch_hn(limit: int = 30, query: str | None = None) -> Iterator[dict]:
    """
    Yield items from HN top stories. Each item: url, title, body, source_type, published_at.
    If query is set, we filter by title (simple substring) for topic relevance.
    """
    try:
        r = requests.get(HN_TOP, timeout=10)
        r.raise_for_status()
        ids = r.json()[:limit]
    except Exception as e:
        logger.warning("HN fetch failed: %s", e)
        return
    for id in ids:
        try:
            r = requests.get(HN_ITEM.format(id=id), timeout=5)
            r.raise_for_status()
            item = r.json()
            if not item:
                continue
            title = item.get("title") or ""
            if query and query.lower() not in title.lower():
                continue
            url = item.get("url") or f"https://news.ycombinator.com/item?id={id}"
            text = item.get("text") or ""
            body = title + "\n\n" + text if text else title
            from datetime import datetime
            ts = item.get("time")
            published_at = datetime.utcfromtimestamp(ts).isoformat() + "Z" if ts else None
            yield {
                "url": url,
                "title": title,
                "body": body[:50000],
                "source_type": "hn",
                "published_at": published_at,
            }
        except Exception as e:
            logger.debug("HN item %s failed: %s", id, e)
            continue

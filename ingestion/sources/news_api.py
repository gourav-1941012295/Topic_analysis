"""NewsAPI.org fetcher (requires NEWS_API_KEY)."""

import os
import logging
from typing import Iterator

logger = logging.getLogger(__name__)


def fetch_news_api(query: str, limit: int = 20, api_key: str | None = None) -> Iterator[dict]:
    """
    Yield articles from NewsAPI.org. Each item: url, title, body, source_type, published_at.
    If no API key, yields nothing.
    """
    try:
        import requests
    except ImportError:
        return
    key = api_key or os.environ.get("NEWS_API_KEY")
    if not key:
        logger.info("NEWS_API_KEY not set; skipping News API")
        return
    url = "https://newsapi.org/v2/everything"
    params = {"q": query, "apiKey": key, "pageSize": min(limit, 100), "sortBy": "publishedAt", "language": "en"}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("News API request failed: %s", e)
        return
    for art in data.get("articles") or []:
        title = art.get("title") or ""
        link = art.get("url") or ""
        desc = art.get("description") or ""
        content = art.get("content") or ""
        body = (title + "\n\n" + desc + "\n\n" + content)[:50000]
        published_at = art.get("publishedAt")
        if not link:
            continue
        yield {
            "url": link,
            "title": title,
            "body": body,
            "source_type": "news_api",
            "published_at": published_at,
        }

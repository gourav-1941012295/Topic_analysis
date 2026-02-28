"""Extract entities, events, and signal tags from each processed doc using LLM."""

import logging
import os
from ingestion.storage import get_connection, get_processed_docs, init_schema, insert_extraction
from config import get_topic_name
from llm import get_client, complete_json

logger = logging.getLogger(__name__)
SIGNAL_TAGS = ["market", "regulation", "technology", "risk", "opportunity"]


def _extract_one(text: str, topic: str) -> dict:
    """One doc → {entities, events, signal_tags}. Uses placeholder if LLM fails."""
    prompt = f'''Analyze this text about "{topic}" and extract:
1. entities: list of companies, people, products, regulations, or geographies (e.g. ["OpenAI", "EU AI Act"])
2. events: list of "who did what, when" (e.g. ["EU passed AI Act in March 2024"])
3. signal_tags: one or more of {SIGNAL_TAGS} (e.g. ["regulation", "risk"])

Text:
---
{text[:8000]}
---

Respond with ONLY a JSON object with keys: entities, events, signal_tags. Arrays only.'''
    out = complete_json(prompt, temperature=0.1)
    if not out:
        if not get_client():
            logger.warning("OpenAI not available; using placeholder extractions.")
        return {"entities": [], "events": [], "signal_tags": ["market"]}
    tags = [t for t in out.get("signal_tags", []) if t in SIGNAL_TAGS] or ["market"]
    return {
        "entities": (out.get("entities") or [])[:30],
        "events": (out.get("events") or [])[:20],
        "signal_tags": tags,
    }


def run_extraction(max_docs: int | None = 50) -> int:
    """Extract entities, events, signal_tags per doc; store in extractions. Returns count."""
    conn = get_connection()
    init_schema(conn)
    docs = get_processed_docs(conn)
    topic = get_topic_name()
    if max_docs:
        docs = docs[:max_docs]
    log_progress = os.environ.get("TRACK_PROGRESS", "").lower() in ("1", "true", "yes")
    count = 0
    for doc in docs:
        text = (doc.get("title") or "") + "\n\n" + (doc.get("body") or "")
        if len(text.strip()) < 50:
            continue
        out = _extract_one(text, topic)
        insert_extraction(conn, doc["id"], out["entities"], out["events"], out["signal_tags"])
        count += 1
        if log_progress and count % 5 == 0:
            logger.info("Extract progress: %s/%s", count, len(docs))
    conn.close()
    logger.info("Extraction: %s docs", count)
    return count

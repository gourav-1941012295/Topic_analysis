"""Trend detection and contradiction detection."""

import logging
import os
from collections import defaultdict
from ingestion.storage import get_connection, get_processed_docs, get_extractions, init_schema, insert_contradiction
from config import get_topic_name
from llm import complete

logger = logging.getLogger(__name__)


def _contradicts(snippet_a: str, snippet_b: str, topic: str) -> bool:
    """True if LLM says the two snippets contradict."""
    prompt = f"""Topic: {topic}
Snippet A: {snippet_a[:1500]}
Snippet B: {snippet_b[:1500]}
Do these CONTRADICT each other (different/opposing facts)? Answer only: YES or NO."""
    ans = complete(prompt, temperature=0)
    return bool(ans and "YES" in (ans or "").upper())


def run_trends_and_contradictions(max_contradiction_pairs: int = 10) -> tuple[dict, list[dict]]:
    """Aggregate extractions into trend summary; find contradictions. Returns (trend_summary, contradictions)."""
    conn = get_connection()
    init_schema(conn)
    docs = get_processed_docs(conn)
    extractions = get_extractions(conn)
    topic = get_topic_name()
    doc_by_id = {d["id"]: d for d in docs}
    ext_by_doc = defaultdict(list)
    for e in extractions:
        ext_by_doc[e["doc_id"]].append(e)

    # Trends
    signal_counts = defaultdict(int)
    entity_counts = defaultdict(int)
    all_events = []
    for e in extractions:
        for t in e.get("signal_tags", []):
            signal_counts[t] += 1
        for ent in e.get("entities", []):
            entity_counts[str(ent)] += 1
        all_events.extend(e.get("events", []))
    trend_summary = {
        "signal_counts": dict(signal_counts),
        "top_entities": sorted(entity_counts.items(), key=lambda x: -x[1])[:25],
        "events_sample": all_events[:30],
        "num_docs": len(docs),
    }

    # Contradictions: sample doc pairs that share an entity
    contradictions_found = []
    doc_ids = [d["id"] for d in docs]
    seen = set()
    for i, doc_id_a in enumerate(doc_ids):
        if len(contradictions_found) >= max_contradiction_pairs:
            break
        entities_a = {str(x) for e in ext_by_doc.get(doc_id_a, []) for x in e.get("entities", [])}
        if not entities_a:
            continue
        for doc_id_b in doc_ids[i + 1 : i + 6]:
            if doc_id_a == doc_id_b:
                continue
            pair = (min(doc_id_a, doc_id_b), max(doc_id_a, doc_id_b))
            if pair in seen:
                continue
            seen.add(pair)
            entities_b = {str(x) for e in ext_by_doc.get(doc_id_b, []) for x in e.get("entities", [])}
            if not (entities_a & entities_b):
                continue
            da, db = doc_by_id.get(doc_id_a, {}), doc_by_id.get(doc_id_b, {})
            sa = (da.get("title") or "") + " " + (da.get("body") or "")[:1200]
            sb = (db.get("title") or "") + " " + (db.get("body") or "")[:1200]
            if _contradicts(sa, sb, topic):
                focus = ", ".join(entities_a & entities_b)[:200]
                insert_contradiction(conn, focus, doc_id_a, doc_id_b, sa[:2000], sb[:2000])
                contradictions_found.append({"focus": focus, "doc_id_a": doc_id_a, "doc_id_b": doc_id_b, "snippet_a": sa[:500], "snippet_b": sb[:500]})
    conn.close()
    logger.info("Trends: %s signals, %s contradictions", len(signal_counts), len(contradictions_found))
    return trend_summary, contradictions_found

"""Synthesize report from docs, extractions, trends, contradictions."""

import json
import logging
from datetime import datetime
from typing import Any
from ingestion.storage import get_connection, get_processed_docs, get_extractions, insert_report
from config import get_topic_name, get_topic_description, get_report_sections
from reasoning.self_critique import run_self_critique
from llm import complete

logger = logging.getLogger(__name__)


def _write_section(
    topic: str,
    description: str,
    evidence: str,
    trend_summary: dict,
    contradictions: list[dict],
    weighting_note: str,
    section: str,
) -> str:
    """One report section with citations."""
    contra_text = "\n".join(
        f"- {c.get('focus', '')}: A: {c.get('snippet_a', '')[:200]}... | B: {c.get('snippet_b', '')[:200]}..."
        for c in contradictions[:5]
    ) if contradictions else "None."
    prompt = f"""Topic: {topic}. Description: {description}
Evidence (cite with [doc_id]):
---
{evidence[:12000]}
---
Trends: {json.dumps(trend_summary)[:1500]}
Contradictions: {contra_text}
{weighting_note}
Write section "{section}" in 2-4 paragraphs. Use ONLY the evidence. Cite every claim with [doc_id]. No invented sources."""
    out = complete(prompt, temperature=0.3)
    return out or f"[Section '{section}' skipped: no LLM]"


def run_synthesis(
    trend_summary: dict,
    contradictions: list[dict],
    weighting_result: dict,
    max_docs_for_context: int = 25,
) -> tuple[dict[str, Any], str, float]:
    """Build evidence, generate sections, self-critique, return (report_json, report_md, confidence)."""
    conn = get_connection()
    docs = get_processed_docs(conn)
    topic = get_topic_name()
    description = get_topic_description()
    sections_config = get_report_sections()
    evidence_docs = docs[:max_docs_for_context]

    # One loop: evidence text + citations list
    evidence_parts = []
    citations_list = []
    for d in evidence_docs:
        did, title, body = d["id"], d.get("title") or "", (d.get("body") or "")[:2000]
        evidence_parts.append(f"[doc_id={did}]\n{title}\n{body}\n")
        citations_list.append({"id": did, "url": d.get("url", ""), "snippet": (title + " " + body)[:200]})
    evidence_with_ids = "\n---\n".join(evidence_parts)
    weighting_note = weighting_result.get("source_summary", "")

    content_sections = [s for s in sections_config if s != "appendix_citations"]
    section_contents = {}
    for sec in content_sections:
        section_contents[sec] = _write_section(
            topic, description, evidence_with_ids, trend_summary, contradictions, weighting_note, sec
        )

    initial_conf = weighting_result.get("weighted_confidence", 0.5)
    final_confidence, critique = run_self_critique(section_contents, topic, initial_conf)

    appendix = "## Appendix: Citations\n" + "\n".join(f"- [{c['id']}] {c['url']}\n  {c['snippet'][:150]}..." for c in citations_list)
    section_contents["appendix_citations"] = appendix

    report_json = {
        "topic": topic,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "sections": {k: {"content": v, "citations": []} for k, v in section_contents.items()},
        "citations": citations_list,
        "confidence": final_confidence,
        "metadata": {"source_weighting": weighting_result, "self_critique": critique, "num_sources": len(docs), "num_contradictions": len(contradictions)},
    }
    md_lines = [f"# {topic}\n", f"*{report_json['generated_at']}*", f"**Confidence: {final_confidence:.2f}**\n"]
    for sec in sections_config:
        if sec in section_contents:
            md_lines.append(f"## {sec.replace('_', ' ').title()}\n\n{section_contents[sec]}\n")
    md_lines.append(f"\n---\n**Self-critique:** {critique}")
    report_md = "\n".join(md_lines)

    insert_report(conn, report_json, report_md, final_confidence)
    conn.close()
    logger.info("Report confidence %.2f", final_confidence)
    return report_json, report_md, final_confidence

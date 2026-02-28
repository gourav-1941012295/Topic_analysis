"""Self-critique: LLM suggests confidence and critique text."""

import logging
from llm import get_client, complete_json

logger = logging.getLogger(__name__)


def run_self_critique(section_contents: dict[str, str], topic: str, initial_confidence: float) -> tuple[float, str]:
    """Returns (adjusted_confidence, critique_text). Blends LLM suggestion with initial."""
    if not get_client():
        logger.warning("OpenAI not available for self-critique.")
        return initial_confidence, "Self-critique skipped (no API)."
    text = "\n\n".join(f"## {k}\n{v[:1500]}" for k, v in section_contents.items())[:6000]
    prompt = f"""Topic: {topic}
Draft report:
---
{text}
---
Review: missing evidence, overclaiming, contradictions. Respond with ONLY JSON: {{"confidence": 0.7, "critique": "one short paragraph"}}"""
    out = complete_json(prompt, temperature=0.2)
    if not out:
        return initial_confidence, "Self-critique parse failed."
    conf = max(0.1, min(0.95, float(out.get("confidence", initial_confidence))))
    critique = out.get("critique") or "No critique provided."
    adjusted = round(0.6 * initial_confidence + 0.4 * conf, 2)
    return adjusted, critique

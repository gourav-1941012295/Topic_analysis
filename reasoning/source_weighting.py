"""Source weighting: confidence from tier and contradictions."""

from typing import Any


def apply_source_weighting(
    docs: list[dict[str, Any]],
    extractions: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Returns {weighted_confidence, source_summary, tier_breakdown}."""
    if not docs:
        return {"weighted_confidence": 0.3, "source_summary": "No sources", "tier_breakdown": {}}
    n = len(docs)
    total_tier = sum(d.get("source_tier", 1) for d in docs)
    avg_tier = total_tier / n
    base = 0.3 + 0.6 * (avg_tier - 1) / 2.0
    penalty = 0.15 * min(len(contradictions), 5)
    confidence = max(0.1, min(0.95, base - penalty))
    tier_counts = {}
    for d in docs:
        t = d.get("source_tier", 1)
        tier_counts[t] = tier_counts.get(t, 0) + 1
    return {
        "weighted_confidence": round(confidence, 2),
        "source_summary": f"{n} sources (tiers: {tier_counts}); {len(contradictions)} contradictions.",
        "tier_breakdown": tier_counts,
    }

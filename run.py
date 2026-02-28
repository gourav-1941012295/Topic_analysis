"""
Autonomous Market Intelligence Agent — full pipeline.

  Ingest → Dedupe & filter → Extract → Trends & contradictions → Source weighting → Report

Run from agent_ai/:  python run.py
  - Prompts: "Which market/area do you want to analyze?" (or pass topic as CLI arg)
  - Example:  python run.py "EV battery supply chain"
Env: OPENAI_API_KEY (required), NEWS_API_KEY (optional), MAX_DOCS_PER_RUN, TRACK_STATUS_FILE
"""

import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

_agent_ai_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_agent_ai_root))

# Load .env
_env_file = _agent_ai_root / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(_env_file)
except ImportError:
    if _env_file.exists():
        with open(_env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if k and v and k not in os.environ:
                        os.environ[k] = v.strip('"').strip("'")

from config import get_topic_name
from ingestion.storage import get_connection, init_schema, get_processed_docs, get_extractions
from ingestion.pipeline import run_ingestion
from processing.dedup_filter import run_dedup_and_filter
from processing.extract import run_extraction
from processing.trends import run_trends_and_contradictions
from reasoning.source_weighting import apply_source_weighting
from report.synthesis import run_synthesis
import tracking

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
MAX_DOCS = int(os.environ.get("MAX_DOCS_PER_RUN", "0")) or None


def _get_topic_from_user() -> str:
    """Ask user which market/area to analyze, or use CLI arg. Returns topic string."""
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()
    print("\nWhich market or area do you want to analyze?")
    print("Examples: AI model providers, EV battery supply chain, fintech regulation, semiconductor geopolitics")
    try:
        topic = input("Enter topic (or press Enter to use config default): ").strip()
    except EOFError:
        topic = ""
    return topic


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set. Set it in .env for extraction and report.")
    # User chooses area to analyze
    user_topic = _get_topic_from_user()
    if user_topic:
        os.environ["TOPIC_OVERRIDE"] = user_topic
        print(f"Analyzing: {user_topic}\n")
    if os.environ.get("TRACK_STATUS_FILE", "1") == "1":
        tracking.set_status_path(_agent_ai_root / "data" / "run_status.json")
    tracking.start_run()
    logger.info("Topic: %s", get_topic_name())

    try:
        tracking.start_step("ingest")
        run_ingestion(max_docs=MAX_DOCS)
        conn = get_connection()
        init_schema(conn)
        raw_count = len(conn.execute("SELECT id FROM raw_docs").fetchall())
        tracking.end_step("ingest", {"raw_docs": raw_count})
        logger.info("Raw docs: %s", raw_count)

        tracking.start_step("dedup_filter")
        processed_count = run_dedup_and_filter()
        tracking.end_step("dedup_filter", {"processed_docs": processed_count})

        tracking.start_step("extract")
        extract_count = run_extraction(max_docs=MAX_DOCS or 50)
        tracking.end_step("extract", {"extractions": extract_count})

        tracking.start_step("trends_contradictions")
        trend_summary, contradictions = run_trends_and_contradictions(max_contradiction_pairs=5)
        tracking.end_step("trends_contradictions", {"contradictions": len(contradictions)})

        tracking.start_step("source_weighting")
        conn = get_connection()
        docs, extractions = get_processed_docs(conn), get_extractions(conn)
        conn.close()
        weighting_result = apply_source_weighting(docs, extractions, contradictions)
        tracking.end_step("source_weighting", {"confidence": weighting_result.get("weighted_confidence")})

        tracking.start_step("synthesis")
        report_json, report_md, confidence = run_synthesis(
            trend_summary, contradictions, weighting_result, max_docs_for_context=20
        )
        tracking.end_step("synthesis", {"confidence": confidence})

        out_dir = _agent_ai_root / "samples"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
        (out_dir / f"report_{stamp}.md").write_text(report_md, encoding="utf-8")
        (out_dir / f"report_{stamp}.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")
        tracking.end_run(success=True)
        logger.info("Report: samples/report_%s.md  Confidence: %.2f", stamp, confidence)
        print("\n--- Preview ---\n", report_md[:1200], "\n--- Done ---")
    except Exception as e:
        logger.exception("Pipeline failed")
        tracking.end_run(success=False, error=str(e))
        raise


if __name__ == "__main__":
    main()

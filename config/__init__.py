"""Load topic and pipeline config from YAML."""

import os
from pathlib import Path
from typing import Any

import yaml

_CONFIG: dict[str, Any] | None = None


def _config_path() -> Path:
    path = Path(__file__).resolve().parent / "topic_config.yaml"
    if not path.exists():
        path = Path(__file__).resolve().parent / "topic_config.example.yaml"
    return path


def load_config() -> dict[str, Any]:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    path = _config_path()
    with open(path) as f:
        _CONFIG = yaml.safe_load(f) or {}
    return _CONFIG


def get_topic_name() -> str:
    """Topic for this run: from user input (env TOPIC_OVERRIDE) or default."""
    override = (os.environ.get("TOPIC_OVERRIDE") or "").strip()
    return override or "Market Intelligence"


def get_topic_description() -> str:
    """Short description used in report synthesis."""
    return "Market, technical, and regulatory landscape for the chosen topic."


def get_time_window_days() -> int:
    return load_config().get("report", {}).get("time_window_days", 30)


def get_report_sections() -> list[str]:
    return load_config().get("report", {}).get("sections", [
        "executive_summary", "market", "regulation", "technology", "risks", "opportunities", "appendix_citations"
    ])


def get_sources() -> dict[str, Any]:
    return load_config().get("sources", {})


def get_advanced_reasoning() -> list[str]:
    return load_config().get("advanced_reasoning", ["contradiction_detection", "source_weighting"])

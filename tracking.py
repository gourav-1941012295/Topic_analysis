"""
Process tracking: step timing, counts, and optional status file for monitoring.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STATUS_PATH: Path | None = None
_START_TIME: float = 0.0
_STEP_START: float = 0.0


def set_status_path(path: str | Path | None) -> None:
    """Set path for run_status.json (e.g. data/run_status.json). None = disabled."""
    global _STATUS_PATH
    _STATUS_PATH = Path(path) if path else None


def _write_status(step: str, status: str, counts: dict[str, Any] | None = None, error: str | None = None) -> None:
    if _STATUS_PATH is None:
        return
    try:
        _STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        elapsed = time.time() - _START_TIME if _START_TIME else 0
        step_elapsed = time.time() - _STEP_START if _STEP_START else 0
        data = {
            "step": step,
            "status": status,
            "elapsed_sec": round(elapsed, 1),
            "step_elapsed_sec": round(step_elapsed, 1),
        }
        if counts:
            data["counts"] = counts
        if error:
            data["error"] = error
        with open(_STATUS_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.debug("Could not write status file: %s", e)


def start_run() -> None:
    """Call at pipeline start. Resets timers and writes initial status."""
    global _START_TIME, _STEP_START
    _START_TIME = time.time()
    _STEP_START = _START_TIME
    _write_status("start", "running", {})


def start_step(step_name: str) -> None:
    """Call at the start of each pipeline step."""
    global _STEP_START
    _STEP_START = time.time()
    _write_status(step_name, "running")
    logger.info("Step: %s (started)", step_name)


def end_step(step_name: str, counts: dict[str, Any] | None = None) -> float:
    """Call at the end of each step. Returns step duration in seconds."""
    elapsed = time.time() - _STEP_START
    _write_status(step_name, "done", counts)
    logger.info("Step: %s done in %.1fs", step_name, elapsed)
    return elapsed


def end_run(success: bool = True, error: str | None = None) -> None:
    """Call when the full pipeline finishes."""
    status = "done" if success else "failed"
    _write_status("end", status, error=error)
    total = time.time() - _START_TIME
    logger.info("Pipeline %s in %.1fs", status, total)


def step_elapsed() -> float:
    """Seconds since start_step was last called."""
    return time.time() - _STEP_START if _STEP_START else 0

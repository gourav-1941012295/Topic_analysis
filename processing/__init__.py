"""Processing: dedupe, filter, extract, trends."""

from .dedup_filter import run_dedup_and_filter
from .extract import run_extraction
from .trends import run_trends_and_contradictions

__all__ = ["run_dedup_and_filter", "run_extraction", "run_trends_and_contradictions"]

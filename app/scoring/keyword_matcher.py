"""Shared keyword-matching helper for the baseline scoring agents.

This is intentionally simple and fully explainable: each agent defines a
set of keyword groups with weights, and matched evidence becomes the
`reasons` returned to the caller. This is a transparent v0 - swapping in an
LLM-based scorer later just means implementing the same BaseScoringAgent
interface.
"""
from app.schemas.evidence import EvidenceItem


def match_evidence(evidence: list[EvidenceItem], keywords: list[str]) -> list[EvidenceItem]:
    """Return evidence items whose label or excerpt contains any keyword (case-insensitive)."""
    lowered_keywords = [k.lower() for k in keywords]
    matched: list[EvidenceItem] = []
    for item in evidence:
        haystack = f"{item.signal_label} {item.excerpt}".lower()
        if any(k in haystack for k in lowered_keywords):
            matched.append(item)
    return matched


def weighted_score(matched_count: int, max_expected: int) -> float:
    """Map a matched-signal count to a 0-100 score, saturating at max_expected."""
    if max_expected <= 0:
        return 0.0
    return round(min(matched_count / max_expected, 1.0) * 100, 1)

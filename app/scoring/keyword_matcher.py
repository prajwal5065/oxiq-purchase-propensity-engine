"""Shared keyword-matching helper for the baseline scoring agents.

This is intentionally simple and fully explainable: each agent defines a
set of keyword groups with weights, and matched evidence becomes the
`reasons` returned to the caller. This is a transparent v0 - swapping in an
LLM-based scorer later just means implementing the same BaseScoringAgent
interface.
"""
import re

from app.schemas.evidence import EvidenceItem
from app.scoring.time_decay import decay_weight

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "its", "their", "is", "are", "was", "were", "has", "have", "had",
    "this", "that", "by", "at", "as", "from", "it", "will", "be", "than",
    "into", "over", "after", "new",
}

# Same-event dedup: two evidence items are treated as describing one
# underlying real-world event (e.g. three outlets covering one funding
# round) when their significant-word overlap clears this threshold and,
# when both dates are known, they fall within EVENT_WINDOW_DAYS of each
# other. Deliberately conservative (high overlap required) so genuinely
# different events in the same category are never merged.
EVENT_SIMILARITY_THRESHOLD = 0.5
EVENT_WINDOW_DAYS = 14


def match_evidence(evidence: list[EvidenceItem], keywords: list[str]) -> list[EvidenceItem]:
    """Return evidence items whose label or excerpt contains any keyword
    (case-insensitive), collapsed so multiple articles/sources describing
    the same underlying event count once (see `dedupe_events`) - otherwise
    N sources covering one event would inflate a pillar's signal count by
    N instead of counting it as the one signal it actually is."""
    lowered_keywords = [k.lower() for k in keywords]
    matched: list[EvidenceItem] = []
    for item in evidence:
        haystack = f"{item.signal_label} {item.excerpt}".lower()
        if any(k in haystack for k in lowered_keywords):
            matched.append(item)
    return dedupe_events(matched)


def _significant_words(item: EvidenceItem) -> set[str]:
    text = f"{item.signal_label} {item.excerpt}".lower()
    return {w for w in _WORD_RE.findall(text) if w not in _STOPWORDS and len(w) > 2}


def dedupe_events(
    evidence: list[EvidenceItem],
    similarity_threshold: float = EVENT_SIMILARITY_THRESHOLD,
    window_days: int = EVENT_WINDOW_DAYS,
) -> list[EvidenceItem]:
    """Collapse multiple evidence items that describe the same underlying
    event into one representative item, so the same real-world event never
    counts as multiple independent signals just because several sources
    reported it.

    Two items are grouped together only when they share a `category`
    *and* their significant words overlap heavily (Jaccard similarity over
    the threshold) *and*, when both have a known publish date, those dates
    fall within `window_days` of each other. All three conditions guard
    against merging genuinely distinct events that merely share a category
    or a few common words. Within a group, the highest-confidence item is
    kept as the representative; the others' sources are folded into its
    label as corroboration so the multi-source signal is still visible
    without inflating the count.
    """
    groups: list[list[EvidenceItem]] = []
    for item in evidence:
        item_words = _significant_words(item)
        placed = False
        for group in groups:
            rep = group[0]
            if item.category != rep.category:
                continue
            rep_words = _significant_words(rep)
            union = item_words | rep_words
            if not union:
                continue
            similarity = len(item_words & rep_words) / len(union)
            if similarity < similarity_threshold:
                continue
            if item.published_at and rep.published_at:
                if abs((item.published_at - rep.published_at).days) > window_days:
                    continue
            group.append(item)
            placed = True
            break
        if not placed:
            groups.append([item])

    representatives: list[EvidenceItem] = []
    for group in groups:
        if len(group) == 1:
            representatives.append(group[0])
            continue
        best = max(group, key=lambda e: e.confidence)
        other_sources = sorted({e.source for e in group if e.source != best.source})
        update: dict = {}
        if other_sources:
            shown = ", ".join(other_sources[:3])
            suffix = f" (also reported by {shown}{', …' if len(other_sources) > 3 else ''})"
            update["signal_label"] = f"{best.signal_label}{suffix}"
            # Corroboration: independent sources agreeing on the same
            # underlying event is itself evidence the fact is real, not
            # just one outlet's error - a small, capped confidence bump
            # per independent extra source (not per raw evidence row,
            # which is what the pre-dedup count would otherwise reward).
            update["confidence"] = round(min(1.0, best.confidence + 0.05 * min(len(other_sources), 3)), 2)
        representatives.append(best.model_copy(update=update) if update else best)
    return representatives


def weighted_score(matched_count: float, max_expected: int) -> float:
    """Map a matched-signal count to a 0-100 score, saturating at max_expected."""
    if max_expected <= 0:
        return 0.0
    return round(min(matched_count / max_expected, 1.0) * 100, 1)


def freshness_weighted_count(matched: list[EvidenceItem]) -> float:
    """Sum of each item's age-decay weight, rather than a flat count of
    matched evidence - so a pillar's saturation point is reached by recent
    signal, not by however many old mentions happen to exist. Mirrors the
    Urgency scorer's original decay-weighted counting, generalized to every
    scorer: an evidence item from 2016-2019 (time_decay's "historical"
    bucket) contributes ~0.05 toward saturation instead of a full 1.0, so
    stale evidence alone can no longer drive a pillar to its ceiling."""
    return sum(decay_weight(item.published_at) for item in matched)

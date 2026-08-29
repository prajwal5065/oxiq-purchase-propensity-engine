"""Contradiction Detector (Decision Intelligence).

Two independent kinds of contradiction, kept deliberately separate:

1. Narrative theme contradictions - the evidence pulls in opposite
   directions on the same theme (e.g. a "hiring spike" signal alongside a
   "layoffs" signal) - so the Decision Engine can discount confidence
   instead of silently picking whichever scorer happened to weigh in
   first.
2. Structured fact contradictions - two evidence items report different
   values for the *same* structured field (e.g. one source says 500
   employees, another says 5,000; one says founded 2015, another says
   2009). This only ever compares a field against itself - employee_count
   against employee_count, founding_year against founding_year - never
   across different fields, since two semantically different facts (an
   employee count and a founding year) are not a contradiction just
   because they're both numbers.

Detected pairs never resolve the contradiction on their own; that's a
judgment call for the human reading the dossier, which is exactly why each
finding cites both pieces of evidence verbatim.
"""
from app.schemas.decision import (
    ContradictionEvidenceRef,
    ContradictionFinding,
    ContradictionReport,
    ContradictionSeverity,
)
from app.schemas.evidence import EvidenceItem

# Structured numeric/date fields compared for internal disagreement.
# (attribute name on EvidenceItem, human label, severity, relative
# tolerance below which two values are treated as the same fact rather
# than a conflict - e.g. rounding/as-of-date differences between two
# legitimate sources, not a real disagreement).
_STRUCTURED_FACT_FIELDS: list[tuple[str, str, ContradictionSeverity, float]] = [
    ("employee_count", "employee count", ContradictionSeverity.MEDIUM, 0.25),
    ("founding_year", "founding year", ContradictionSeverity.HIGH, 0.0),
]

# (theme, positive phrases, negative phrases, severity, description)
_CONTRADICTION_THEMES: list[tuple[str, list[str], list[str], ContradictionSeverity, str]] = [
    (
        "hiring_trajectory",
        ["hiring spike", "hiring surge", "expanding team", "growing the team"],
        ["hiring freeze", "layoffs", "downsizing", "workforce reduction"],
        ContradictionSeverity.HIGH,
        "Evidence shows both active hiring and layoffs/hiring-freeze signals.",
    ),
    (
        "financial_trajectory",
        ["funding round", "raises", "series a", "series b", "series c"],
        ["funding cut", "budget cuts", "cost-cutting", "runway concerns"],
        ContradictionSeverity.HIGH,
        "Evidence shows both a funding event and cost-cutting/budget-cut signals.",
    ),
    (
        "footprint_trajectory",
        ["expansion", "new office", "opens office"],
        ["office closure", "downsizing", "consolidating offices"],
        ContradictionSeverity.MEDIUM,
        "Evidence shows both physical expansion and contraction signals.",
    ),
    (
        "technology_posture",
        ["adopts ai", "ai adoption", "digital transformation", "cloud migration"],
        ["legacy system", "resistant to change", "no budget for tech"],
        ContradictionSeverity.MEDIUM,
        "Evidence shows both technology-adoption momentum and resistance-to-change signals.",
    ),
]


class ContradictionDetector:
    def detect(self, evidence: list[EvidenceItem]) -> ContradictionReport:
        findings: list[ContradictionFinding] = []
        for theme, positive_phrases, negative_phrases, severity, description in _CONTRADICTION_THEMES:
            positives = self._match(evidence, positive_phrases)
            negatives = self._match(evidence, negative_phrases)
            if positives and negatives:
                findings.append(
                    ContradictionFinding(
                        theme=theme,
                        severity=severity,
                        description=description,
                        evidence_a=self._ref(positives[0]),
                        evidence_b=self._ref(negatives[0]),
                    )
                )

        findings.extend(self._detect_structured_fact_conflicts(evidence))

        return ContradictionReport(
            has_contradictions=bool(findings),
            findings=findings,
            summary=self._summary(findings),
        )

    @classmethod
    def _detect_structured_fact_conflicts(cls, evidence: list[EvidenceItem]) -> list[ContradictionFinding]:
        """Compare each structured fact field against itself across
        sources - never against a different field - and flag genuine
        disagreement (outside `tolerance`), not the ordinary case of every
        source simply agreeing (or only one source having reported the
        fact at all, which is missing evidence, not a contradiction)."""
        findings: list[ContradictionFinding] = []
        for field_name, label, severity, tolerance in _STRUCTURED_FACT_FIELDS:
            reported: list[tuple[EvidenceItem, float]] = [
                (item, getattr(item, field_name))
                for item in evidence
                if getattr(item, field_name, None) is not None
            ]
            if len(reported) < 2:
                continue

            for i in range(len(reported)):
                item_a, value_a = reported[i]
                for item_b, value_b in reported[i + 1 :]:
                    if value_a == value_b:
                        continue
                    larger = max(abs(value_a), abs(value_b)) or 1
                    relative_diff = abs(value_a - value_b) / larger
                    if relative_diff <= tolerance:
                        continue
                    findings.append(
                        ContradictionFinding(
                            theme=f"{field_name}_conflict",
                            severity=severity,
                            description=(
                                f"Sources disagree on {label}: {item_a.source} reports "
                                f"{value_a:g} while {item_b.source} reports {value_b:g}."
                            ),
                            evidence_a=cls._ref(item_a),
                            evidence_b=cls._ref(item_b),
                        )
                    )
        return findings

    @staticmethod
    def _match(evidence: list[EvidenceItem], phrases: list[str]) -> list[EvidenceItem]:
        lowered = [p.lower() for p in phrases]
        return [
            item
            for item in evidence
            if any(p in f"{item.signal_label} {item.excerpt}".lower() for p in lowered)
        ]

    @staticmethod
    def _ref(item: EvidenceItem) -> ContradictionEvidenceRef:
        return ContradictionEvidenceRef(
            evidence_id=item.id, label=item.signal_label, excerpt=item.excerpt, source=item.source
        )

    @staticmethod
    def _summary(findings: list[ContradictionFinding]) -> str:
        if not findings:
            return "No contradictory evidence detected."
        themes = ", ".join(f.theme.replace("_", " ") for f in findings)
        return f"{len(findings)} contradiction(s) found: {themes}."

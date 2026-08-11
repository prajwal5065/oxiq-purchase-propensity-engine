"""Contradiction Detector (Decision Intelligence).

Flags when the evidence pulls in opposite directions on the same theme -
e.g. a "hiring spike" signal alongside a "layoffs" signal - so the Decision
Engine can discount confidence instead of silently picking whichever
scorer happened to weigh in first. Detected pairs never resolve the
contradiction on their own; that's a judgment call for the human reading
the dossier, which is exactly why each finding cites both pieces of
evidence verbatim.
"""
from app.schemas.decision import (
    ContradictionEvidenceRef,
    ContradictionFinding,
    ContradictionReport,
    ContradictionSeverity,
)
from app.schemas.evidence import EvidenceItem

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

        return ContradictionReport(
            has_contradictions=bool(findings),
            findings=findings,
            summary=self._summary(findings),
        )

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

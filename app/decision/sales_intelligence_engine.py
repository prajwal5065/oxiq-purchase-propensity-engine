"""Sales Intelligence Engine.

Thin composition layer that converts already-computed Decision Intelligence
outputs into a sales-action-oriented bundle.  No I/O, no new external APIs,
no new scoring system.

Architecture contract
---------------------
- Input:  DecisionIntelligence (already built by DecisionIntelligenceEngine),
          list[EvidenceItem], PurchaseScoreResult, DisqualificationExplanation
- Output: SalesIntelligence

Every finding carries ``evidence_ids`` pointing back to the exact
EvidenceItem(s) that produced it.  When Decision Intelligence reported
INSUFFICIENT_DATA, ``build()`` returns immediately with ``data_sufficient=False``
and every narrative field set to an explicit explanation - never a silent null.

Stakeholder roles are role titles only (e.g. 'VP Engineering', 'Head of AI');
the engine never produces a proper noun or individual name.  A role is only
included when at least one evidence item contains a phrase that mentions it.

The ``_build_next_action`` method is evidence-backed and priority-driven:
  HIGH_PRIORITY + strong trigger → "Prioritize outreach and reference the trigger."
  MEDIUM_PRIORITY               → "Add to nurture and monitor for new signals."
  LOW_PRIORITY                  → "Do not prioritize."
  INSUFFICIENT_DATA             → "Gather more evidence before outreach."
"""
import uuid
from typing import TYPE_CHECKING

from app.schemas.decision import BuyingIntentLevel, DecisionPriority
from app.schemas.evidence import EvidenceItem
from app.schemas.explanation import DisqualificationExplanation
from app.schemas.sales import (
    OpportunityItem,
    SalesAction,
    SalesIntelligence,
    SalesRisk,
    SalesTrigger,
    SolutionFitItem,
    StakeholderRole,
)

if TYPE_CHECKING:
    from app.schemas.decision import DecisionIntelligence
    from app.schemas.score import PurchaseScoreResult

# ---------------------------------------------------------------------------
# Opportunity detection – keyword groups with associated opportunity labels.
# Each entry: (opportunity_label, [keyword_phrases...])
# ---------------------------------------------------------------------------
_OPPORTUNITY_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "AI / ML initiative underway",
        [
            "machine learning", "artificial intelligence", "generative ai",
            "llm", "ai initiative", "ai adoption", "hiring ai", "ml engineer",
        ],
    ),
    (
        "Active digital transformation programme",
        [
            "digital transformation", "cloud migration", "cloud-native",
            "modernisation", "modernization", "platform migration",
        ],
    ),
    (
        "Growth event creating new capacity needs",
        [
            "funding round", "series a", "series b", "series c",
            "raised", "new investment", "expansion", "new office",
        ],
    ),
    (
        "Hiring spike signals increased operational need",
        [
            "hiring spike", "hiring surge", "expanding team",
            "growing the team", "engineering hiring", "recruiting",
        ],
    ),
    (
        "New product / platform launch",
        [
            "product launch", "unveils", "launches", "new platform",
            "new product",
        ],
    ),
]

# ---------------------------------------------------------------------------
# Solution fit mapping – (use_case_label, keyword_phrases)
# Evaluated in order; first match wins.
# ---------------------------------------------------------------------------
_SOLUTION_FIT_MAP: list[tuple[str, list[str]]] = [
    (
        "AI/ML Platform Adoption",
        [
            "machine learning", "artificial intelligence", "generative ai",
            "llm", "ai engineer", "ml engineer", "deep learning",
            "ai platform", "neural", "nlp",
        ],
    ),
    (
        "Cloud Infrastructure Modernisation",
        [
            "cloud migration", "aws", "azure", "gcp", "kubernetes",
            "cloud-native", "microservices", "devops", "ci/cd",
        ],
    ),
    (
        "Digital Transformation Enablement",
        [
            "digital transformation", "self-service platform",
            "saas", "api-first", "platform modernisation",
        ],
    ),
    (
        "Talent & Capacity Expansion",
        [
            "hiring spike", "hiring surge", "expanding team",
            "talent acquisition", "workforce growth",
        ],
    ),
    (
        "Growth & Expansion Support",
        [
            "funding round", "series a", "series b", "series c",
            "new office", "expansion", "market entry",
        ],
    ),
]

# ---------------------------------------------------------------------------
# Stakeholder role detection – (role_title, keyword_phrases)
# A role is only included when evidence actually mentions it.
# ---------------------------------------------------------------------------
_ROLE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("CTO",            ["cto", "chief technology officer"]),
    ("VP Engineering", ["vp engineering", "vice president engineering", "vp of engineering"]),
    ("Head of AI",     ["head of ai", "head of machine learning", "head of ml", "director of ai"]),
    ("Chief Digital Officer", ["cdo", "chief digital officer"]),
    ("VP Product",     ["vp product", "vice president product", "head of product"]),
    ("IT Director",    ["it director", "director of it", "director of information technology"]),
    ("CIO",            ["cio", "chief information officer"]),
    ("Engineering Manager", ["engineering manager", "head of engineering", "engineering lead"]),
]

# ---------------------------------------------------------------------------
# Existing-vendor risk detection – competing / incumbent product keywords
# ---------------------------------------------------------------------------
_EXISTING_VENDOR_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Salesforce",  ["salesforce", "sfdc"]),
    ("HubSpot",     ["hubspot"]),
    ("SAP",         ["sap erp", "sap hana", " sap "]),
    ("Workday",     ["workday"]),
    ("ServiceNow",  ["servicenow"]),
    ("Microsoft 365 / Teams", ["microsoft teams", "microsoft 365", "m365"]),
    ("Zendesk",     ["zendesk"]),
    ("Databricks",  ["databricks"]),
    ("Snowflake",   ["snowflake"]),
]

_INSUFFICIENT_DATA_MSG = (
    "Insufficient data — Decision Intelligence flagged INSUFFICIENT_DATA; "
    "gather more evidence before making sales assertions."
)


def _haystack(item: EvidenceItem) -> str:
    return f"{item.signal_label} {item.excerpt}".lower()


def _collect_all_evidence_ids(intel: "SalesIntelligence") -> list[uuid.UUID]:
    """Union of every evidence_id referenced across sub-fields."""
    seen: set[uuid.UUID] = set()
    if intel.opportunity:
        seen.update(intel.opportunity.evidence_ids)
    if intel.solution_fit:
        seen.update(intel.solution_fit.evidence_ids)
    for role in intel.likely_buyer_roles:
        seen.update(role.evidence_ids)
    if intel.sales_trigger and intel.sales_trigger.evidence_id:
        seen.add(intel.sales_trigger.evidence_id)
    for risk in intel.risks:
        seen.update(risk.evidence_ids)
    if intel.recommended_next_action:
        seen.update(intel.recommended_next_action.evidence_ids)
    return list(seen)


class SalesIntelligenceEngine:
    """Converts a DecisionIntelligence bundle into a SalesIntelligence bundle.

    All public state is read-only; the engine is safe to reuse across calls.
    """

    def build(
        self,
        evidence: list[EvidenceItem],
        decision_intelligence: "DecisionIntelligence",
        purchase_result: "PurchaseScoreResult",
        disqualification: DisqualificationExplanation,
    ) -> SalesIntelligence:
        recommendation = decision_intelligence.recommendation

        # ---------------------------------------------------------------
        # INSUFFICIENT_DATA guardrail: propagate explicitly.
        # ---------------------------------------------------------------
        if recommendation.priority == DecisionPriority.INSUFFICIENT_DATA:
            action = SalesAction(
                action="Gather more evidence before outreach.",
                rationale=_INSUFFICIENT_DATA_MSG,
                evidence_ids=[],
            )
            risk = SalesRisk(
                description=_INSUFFICIENT_DATA_MSG,
                risk_type="missing_evidence",
                evidence_ids=[],
            )
            result = SalesIntelligence(
                opportunity=None,
                solution_fit=None,
                likely_buyer_roles=[],
                sales_trigger=None,
                risks=[risk],
                recommended_next_action=action,
                evidence_ids=[],
                confidence=0.0,
                data_sufficient=False,
            )
            return result

        # ---------------------------------------------------------------
        # Normal path – all sub-builders are evidence-backed.
        # ---------------------------------------------------------------
        opportunity = self._build_opportunity(evidence)
        solution_fit = self._build_solution_fit(evidence, purchase_result)
        stakeholder_roles = self._build_stakeholder_roles(evidence)
        sales_trigger = self._build_sales_trigger(recommendation.why_now)
        risks = self._build_risks(
            contradictions=recommendation.contradictions,
            disqualification=disqualification,
            evidence=evidence,
        )
        next_action = self._build_next_action(
            priority=recommendation.priority,
            trigger=sales_trigger,
            buying_intent=recommendation.buying_intent,
            opportunity=opportunity,
        )

        # Overall confidence: blend of decision score and evidence quality.
        decision_score = recommendation.decision_score or 0.0
        avg_evidence_conf = (
            sum(e.confidence for e in evidence) / len(evidence)
            if evidence else 0.0
        )
        confidence = round((decision_score * 0.6 + avg_evidence_conf * 0.4), 2)

        partial = SalesIntelligence(
            opportunity=opportunity,
            solution_fit=solution_fit,
            likely_buyer_roles=stakeholder_roles,
            sales_trigger=sales_trigger,
            risks=risks,
            recommended_next_action=next_action,
            evidence_ids=[],          # computed below
            confidence=min(confidence, 1.0),
            data_sufficient=True,
        )
        partial.evidence_ids = _collect_all_evidence_ids(partial)
        return partial

    # ------------------------------------------------------------------
    # Sub-builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_opportunity(evidence: list[EvidenceItem]) -> OpportunityItem | None:
        """Return the highest-confidence opportunity supported by evidence.

        Iterates opportunity keyword groups in priority order and collects all
        matching evidence items for the *first* group that matches anything.
        """
        for label, phrases in _OPPORTUNITY_KEYWORDS:
            matched: list[EvidenceItem] = [
                item
                for item in evidence
                if any(p in _haystack(item) for p in phrases)
            ]
            if matched:
                # Confidence = average of matched items' extraction confidence.
                avg_conf = sum(m.confidence for m in matched) / len(matched)
                return OpportunityItem(
                    description=label,
                    evidence_ids=[m.id for m in matched],
                    confidence=round(avg_conf, 2),
                )
        return None

    @staticmethod
    def _build_solution_fit(
        evidence: list[EvidenceItem],
        purchase_result: "PurchaseScoreResult",
    ) -> SolutionFitItem | None:
        """Map evidence to the best-fit use-case from the fixed taxonomy."""
        for use_case, phrases in _SOLUTION_FIT_MAP:
            matched: list[EvidenceItem] = [
                item
                for item in evidence
                if any(p in _haystack(item) for p in phrases)
            ]
            if matched:
                reasons = ", ".join(
                    m.signal_label for m in matched[:3]   # cap at 3 for readability
                )
                avg_conf = sum(m.confidence for m in matched) / len(matched)
                return SolutionFitItem(
                    use_case=use_case,
                    fit_reasoning=f"Evidence supports '{use_case}': {reasons}.",
                    evidence_ids=[m.id for m in matched],
                    confidence=round(avg_conf, 2),
                )

        # Fallback: use the top purchase pillar if we have scores.
        if purchase_result.pillar_scores:
            top = max(purchase_result.pillar_scores, key=lambda p: p.score)
            if top.score >= 40.0:
                return SolutionFitItem(
                    use_case="General Business Capability Improvement",
                    fit_reasoning=(
                        f"Top scoring pillar '{top.score_type.value.replace('_', ' ')}' "
                        f"({top.score:.0f}/100) suggests capability-level fit."
                    ),
                    evidence_ids=[],
                    confidence=round(top.confidence * 0.6, 2),
                )
        return None

    @staticmethod
    def _build_stakeholder_roles(evidence: list[EvidenceItem]) -> list[StakeholderRole]:
        """Return role titles directly supported by evidence.

        Each role is only included when at least one evidence item's text
        contains a phrase for that role.  No proper nouns / individual names
        are produced.
        """
        roles: list[StakeholderRole] = []
        for role_title, phrases in _ROLE_KEYWORDS:
            matched: list[EvidenceItem] = [
                item
                for item in evidence
                if any(p in _haystack(item) for p in phrases)
            ]
            if matched:
                rationale = (
                    f"Evidence mentions '{role_title}' role: "
                    f"{matched[0].signal_label} ({matched[0].source})."
                )
                roles.append(
                    StakeholderRole(
                        role_title=role_title,
                        rationale=rationale,
                        evidence_ids=[m.id for m in matched],
                    )
                )
        return roles

    @staticmethod
    def _build_sales_trigger(why_now) -> SalesTrigger | None:
        """Directly wrap the top WhyNowTrigger — no recomputation."""
        if not why_now.has_timing_trigger or not why_now.triggers:
            return None
        top = why_now.triggers[0]
        return SalesTrigger(
            trigger_type=top.trigger_type,
            label=top.label,
            excerpt=top.excerpt,
            source=top.source,
            evidence_id=top.evidence_id,
            freshness_label=top.freshness_label,
            narrative=why_now.narrative,
        )

    @staticmethod
    def _build_risks(
        contradictions,
        disqualification: DisqualificationExplanation,
        evidence: list[EvidenceItem],
    ) -> list[SalesRisk]:
        risks: list[SalesRisk] = []

        # 1. Contradiction risks – directly from ContradictionReport.
        for finding in contradictions.findings:
            evidence_ids = [
                eid
                for eid in [
                    finding.evidence_a.evidence_id,
                    finding.evidence_b.evidence_id,
                ]
                if eid is not None
            ]
            risks.append(
                SalesRisk(
                    description=(
                        f"Contradictory signals on '{finding.theme.replace('_', ' ')}': "
                        f"{finding.description}"
                    ),
                    risk_type="contradiction",
                    evidence_ids=evidence_ids,
                )
            )

        # 2. Missing evidence risks – from DisqualificationExplanation.
        for missing in disqualification.missing_evidence:
            risks.append(
                SalesRisk(
                    description=f"Missing evidence: {missing}",
                    risk_type="missing_evidence",
                    evidence_ids=[],
                )
            )

        # 3. Existing vendor risks – keyword scan over evidence.
        for vendor_label, phrases in _EXISTING_VENDOR_KEYWORDS:
            matched: list[EvidenceItem] = [
                item
                for item in evidence
                if any(p in _haystack(item) for p in phrases)
            ]
            if matched:
                risks.append(
                    SalesRisk(
                        description=(
                            f"Existing technology / vendor detected: {vendor_label} — "
                            "may represent an incumbent that needs to be displaced."
                        ),
                        risk_type="existing_vendor",
                        evidence_ids=[m.id for m in matched],
                    )
                )

        return risks

    @staticmethod
    def _build_next_action(
        priority: DecisionPriority,
        trigger: SalesTrigger | None,
        buying_intent,
        opportunity: OpportunityItem | None,
    ) -> SalesAction:
        """Evidence-backed, priority-driven next action — deterministic, no LLM."""
        trigger_ids: list[uuid.UUID] = (
            [trigger.evidence_id] if trigger and trigger.evidence_id else []
        )
        opportunity_ids: list[uuid.UUID] = (
            opportunity.evidence_ids if opportunity else []
        )
        action_evidence_ids = list({*trigger_ids, *opportunity_ids})

        if priority == DecisionPriority.INSUFFICIENT_DATA:
            return SalesAction(
                action="Gather more evidence before outreach.",
                rationale=_INSUFFICIENT_DATA_MSG,
                evidence_ids=[],
            )

        if priority == DecisionPriority.HIGH_PRIORITY:
            if trigger:
                rationale = (
                    f"High-priority company with a fresh '{trigger.trigger_type.replace('_', ' ')}' trigger "
                    f"({trigger.freshness_label}): {trigger.label}. "
                    "Referencing this event makes outreach timely and specific."
                )
                action_text = (
                    "Prioritize outreach and reference the trigger: "
                    f"'{trigger.label}'."
                )
            elif buying_intent.level in (
                BuyingIntentLevel.STRONG, BuyingIntentLevel.MODERATE
            ):
                rationale = (
                    f"High-priority company with {buying_intent.level.value} buying intent "
                    "but no single dated trigger event. Lead with the strongest buying signal."
                )
                action_text = "Prioritize outreach and reference the strongest buying intent evidence."
                action_evidence_ids = [
                    s.evidence_id
                    for s in buying_intent.matched_signals[:3]
                    if s.evidence_id
                ]
            else:
                rationale = (
                    "High-priority company based on purchase score, though no specific "
                    "trigger or strong buying-intent signal was detected."
                )
                action_text = "Prioritize outreach using the best available evidence."
            return SalesAction(
                action=action_text,
                rationale=rationale,
                evidence_ids=action_evidence_ids,
            )

        if priority == DecisionPriority.MEDIUM_PRIORITY:
            return SalesAction(
                action="Add to nurture and monitor for new signals.",
                rationale=(
                    "Medium-priority company: add to a nurture sequence and monitor "
                    "for fresh urgency signals (funding, hiring, expansion) before a direct pitch."
                ),
                evidence_ids=action_evidence_ids,
            )

        # LOW_PRIORITY (or anything else)
        return SalesAction(
            action="Do not prioritize.",
            rationale=(
                "Low-priority company: deprioritize for now; revisit if new funding, "
                "hiring, or product signals appear."
            ),
            evidence_ids=[],
        )

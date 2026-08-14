import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { BuyingIntentPanel } from "../components/BuyingIntentPanel";
import { ChangeAnalysisPanel } from "../components/ChangeAnalysisPanel";
import { ConfidenceExplanationPanel } from "../components/ConfidenceExplanationPanel";
import { ContradictionsPanel } from "../components/ContradictionsPanel";
import { DisqualificationPanel } from "../components/DisqualificationPanel";
import { DossierNav } from "../components/DossierNav";
import { EvidenceCoverageSection } from "../components/EvidenceCoverageSection";
import { EvidenceLog } from "../components/EvidenceLog";
import { EvidenceSection } from "../components/EvidenceSection";
import { ExplanationHeadline } from "../components/ExplanationHeadline";
import { JobsPanel } from "../components/JobsPanel";
import { PillarExplanationCard } from "../components/PillarExplanationCard";
import { PillarRadar } from "../components/PillarRadar";
import { PriorityStamp } from "../components/PriorityStamp";
import { RecommendationPanel } from "../components/RecommendationPanel";
import { SalesIntelligenceSection } from "../components/SalesIntelligenceSection";
import { ScoreDial } from "../components/ScoreDial";
import { TechnologyPanel } from "../components/TechnologyPanel";
import { WhyNowPanel } from "../components/WhyNowPanel";
import { formatRelativeDate, priorityFromScore } from "../lib/format";
import type {
  AnalysisExplanation,
  CompanySummary,
  EvidenceRecord,
  PillarScore,
  RecommendationResult,
} from "../types";

interface DossierData {
  company: CompanySummary;
  pillars: PillarScore[];
  purchaseScore: number;
  purchaseConfidence: number;
  recommendation: RecommendationResult | null;
  explanation: AnalysisExplanation | null;
  evidence: EvidenceRecord[];
}

const NAV_ITEMS = [
  { id: "decision", label: "Final Decision" },
  { id: "decision-intelligence", label: "Decision Intelligence" },
  { id: "sales-intelligence", label: "Sales Intelligence" },
  { id: "pillars", label: "Pillars" },
  { id: "evidence", label: "Evidence" },
  { id: "technology", label: "Technology" },
  { id: "jobs", label: "Jobs" },
];

function SectionHeading({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="font-mono text-[10px] uppercase tracking-widest text-paper-faint mb-4 scroll-mt-16">
      {children}
    </h2>
  );
}

export function CompanyPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<DossierData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setData(null);
    setError(null);

    Promise.all([
      api.getCompany(id),
      api.getScores(id),
      api.getRecommendation(id),
      api.getExplanation(id),
      api.getEvidence(id).catch(() => [] as EvidenceRecord[]),
    ])
      .then(([company, scores, recommendation, explanation, evidence]) => {
        if (cancelled) return;
        const purchase = scores.find((s) => s.score_type === "purchase_propensity");
        const pillars = scores.filter((s) => s.score_type !== "purchase_propensity");
        setData({
          company,
          pillars,
          purchaseScore: purchase?.score ?? 0,
          purchaseConfidence: purchase?.confidence ?? 0,
          recommendation,
          explanation,
          evidence,
        });
      })
      .catch(() => !cancelled && setError("Couldn't pull this dossier. It may not exist."));

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center">
        <p className="font-mono text-xs text-rose mb-4">{error}</p>
        <Link to="/" className="font-mono text-xs text-signal hover:underline">
          &larr; Back to index
        </Link>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-10 animate-pulse-glow">
        <div className="h-3 w-32 bg-ink-700 rounded-sm mb-8" />
        <div className="h-8 w-64 bg-ink-700 rounded-sm mb-3" />
        <div className="h-3 w-40 bg-ink-700 rounded-sm mb-10" />
        <div className="grid md:grid-cols-2 gap-6">
          <div className="h-48 bg-ink-800 border border-ink-600 rounded-sm" />
          <div className="h-48 bg-ink-800 border border-ink-600 rounded-sm" />
        </div>
      </div>
    );
  }

  // The explanation endpoint carries the real, structured decision. Fall
  // back to the old zero-score heuristic only for companies analyzed
  // before this endpoint existed (explanation === null, e.g. a 404).
  const finalDecision = data.explanation?.disqualification.final_decision;
  const disqualified = finalDecision
    ? finalDecision !== "qualified"
    : data.purchaseScore === 0 && data.purchaseConfidence === 0;
  const priority = data.recommendation?.contact_priority ?? priorityFromScore(data.purchaseScore, disqualified);
  const decisionIntelligence = data.explanation?.decision_intelligence;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <Link to="/" className="font-mono text-xs text-paper-faint hover:text-signal transition-colors">
        &larr; Dossier index
      </Link>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="font-display text-3xl text-paper">{data.company.name}</h1>
          <div className="flex items-center gap-3 mt-1">
            <p className="font-mono text-sm text-paper-dim">{data.company.domain}</p>
            {data.company.industry && (
              <span className="font-mono text-[10px] uppercase tracking-wide text-paper-faint border border-ink-600 rounded-sm px-1.5 py-0.5">
                {data.company.industry}
              </span>
            )}
          </div>
          <p className="font-mono text-[10px] text-paper-faint mt-2">
            last processed {formatRelativeDate(data.company.last_processed_at)}
          </p>
        </div>
        <PriorityStamp priority={priority} disqualified={disqualified} />
      </div>

      <DossierNav items={NAV_ITEMS} />

      {/* 1. FINAL DECISION */}
      <section className="mb-10">
        <SectionHeading id="decision">Final Decision</SectionHeading>

        {data.explanation && <ExplanationHeadline headline={data.explanation.headline} />}

        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div className="border border-ink-600 bg-ink-800 rounded-sm p-6 flex items-center justify-center">
            <ScoreDial
              score={data.purchaseScore}
              confidence={data.purchaseConfidence}
              disqualified={disqualified}
            />
          </div>
          <div className="border border-ink-600 bg-ink-800 rounded-sm p-6 flex items-center justify-center">
            <PillarRadar pillars={data.pillars} />
          </div>
        </div>

        {data.explanation && data.explanation.disqualification.final_decision !== "qualified" && (
          <div className="mb-6">
            <DisqualificationPanel disqualification={data.explanation.disqualification} />
          </div>
        )}

        {data.explanation && (
          <ConfidenceExplanationPanel confidence={data.explanation.confidence_explanation} />
        )}

        {data.recommendation && (
          <div className="mt-6">
            <RecommendationPanel recommendation={data.recommendation} disqualified={disqualified} />
          </div>
        )}
      </section>

      {/* 2. DECISION INTELLIGENCE */}
      <section className="mb-10">
        <SectionHeading id="decision-intelligence">Decision Intelligence</SectionHeading>

        {decisionIntelligence ? (
          <div className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              <BuyingIntentPanel intent={decisionIntelligence.recommendation.buying_intent} />
              <WhyNowPanel whyNow={decisionIntelligence.recommendation.why_now} />
            </div>
            <ContradictionsPanel contradictions={decisionIntelligence.recommendation.contradictions} />
            <ChangeAnalysisPanel changeAnalysis={decisionIntelligence.change_analysis} />
            {data.explanation && <EvidenceCoverageSection coverage={data.explanation.evidence_coverage} />}
          </div>
        ) : (
          <div className="border border-dashed border-ink-500 rounded-sm p-8 text-center">
            <p className="font-mono text-xs uppercase tracking-wider text-paper-faint mb-1">
              Decision Intelligence unavailable
            </p>
            <p className="text-sm text-paper-dim max-w-md mx-auto">
              This analysis predates the Decision Intelligence feature, or hasn&rsquo;t completed yet.
            </p>
          </div>
        )}
      </section>

      {/* 3. SALES INTELLIGENCE */}
      <section className="mb-10">
        <SectionHeading id="sales-intelligence">Sales Intelligence</SectionHeading>
        <SalesIntelligenceSection sales={data.explanation?.sales_intelligence ?? null} />
      </section>

      {/* Pillar breakdown */}
      <section className="mb-10">
        <SectionHeading id="pillars">Pillars</SectionHeading>
        {data.explanation && data.explanation.pillar_explanations.length > 0 ? (
          <div className="space-y-3">
            {data.explanation.pillar_explanations.map((pillar) => (
              <PillarExplanationCard key={pillar.score_type} pillar={pillar} />
            ))}
          </div>
        ) : (
          <EvidenceLog pillars={data.pillars} />
        )}
      </section>

      {/* 4. EVIDENCE */}
      <section className="mb-10">
        <SectionHeading id="evidence">Evidence ({data.evidence.length})</SectionHeading>
        <EvidenceSection evidence={data.evidence} explanation={data.explanation} />
      </section>

      {/* 5. TECHNOLOGY */}
      <section className="mb-10">
        <SectionHeading id="technology">Technology</SectionHeading>
        <TechnologyPanel evidence={data.evidence} />
      </section>

      {/* 6. JOBS */}
      <section>
        <SectionHeading id="jobs">Jobs</SectionHeading>
        <JobsPanel evidence={data.evidence} />
      </section>
    </div>
  );
}

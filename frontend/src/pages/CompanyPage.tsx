import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { EvidenceLog } from "../components/EvidenceLog";
import { PillarRadar } from "../components/PillarRadar";
import { PriorityStamp } from "../components/PriorityStamp";
import { RecommendationPanel } from "../components/RecommendationPanel";
import { ScoreDial } from "../components/ScoreDial";
import { formatRelativeDate, priorityFromScore } from "../lib/format";
import type { CompanySummary, PillarScore, RecommendationResult } from "../types";

interface DossierData {
  company: CompanySummary;
  pillars: PillarScore[];
  purchaseScore: number;
  purchaseConfidence: number;
  recommendation: RecommendationResult | null;
}

export function CompanyPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<DossierData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    Promise.all([api.getCompany(id), api.getScores(id), api.getRecommendation(id)])
      .then(([company, scores, recommendation]) => {
        if (cancelled) return;
        const purchase = scores.find((s) => s.score_type === "purchase_propensity");
        const pillars = scores.filter((s) => s.score_type !== "purchase_propensity");
        setData({
          company,
          pillars,
          purchaseScore: purchase?.score ?? 0,
          purchaseConfidence: purchase?.confidence ?? 0,
          recommendation,
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
      <div className="max-w-3xl mx-auto px-6 py-16 text-center">
        <p className="font-mono text-xs uppercase tracking-widest text-paper-faint animate-pulse-glow">
          Pulling dossier&hellip;
        </p>
      </div>
    );
  }

  // The Rule Engine's only current disqualifier fires exactly when overall
  // confidence hits zero, which also zeroes the purchase score - so this
  // combination reliably signals "disqualified" without a dedicated API field.
  const disqualified = data.purchaseScore === 0 && data.purchaseConfidence === 0;
  const priority = data.recommendation?.contact_priority ?? priorityFromScore(data.purchaseScore, disqualified);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <Link to="/" className="font-mono text-xs text-paper-faint hover:text-signal transition-colors">
        &larr; Dossier index
      </Link>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4 mb-8">
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

      <div className="grid md:grid-cols-2 gap-6 mb-10">
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

      {data.recommendation && (
        <div className="mb-10">
          <RecommendationPanel recommendation={data.recommendation} disqualified={disqualified} />
        </div>
      )}

      <div>
        <h2 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint mb-4">
          Evidence log
        </h2>
        <EvidenceLog pillars={data.pillars} />
      </div>
    </div>
  );
}

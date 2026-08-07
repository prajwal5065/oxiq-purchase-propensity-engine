import type { ReactNode } from "react";
import type { RecommendationResult } from "../types";
import { PriorityStamp } from "./PriorityStamp";

export function RecommendationPanel({
  recommendation,
  disqualified,
}: {
  recommendation: RecommendationResult;
  disqualified: boolean;
}) {
  return (
    <div className="border border-ink-600 bg-ink-800 rounded-sm p-6">
      <div className="flex items-start justify-between gap-4 mb-4">
        <h3 className="font-display text-lg text-paper">Field brief</h3>
        <PriorityStamp priority={recommendation.contact_priority} disqualified={disqualified} size="sm" />
      </div>

      <p className="text-sm leading-relaxed text-paper-dim mb-6">{recommendation.executive_summary}</p>

      {recommendation.fit_reasons.length > 0 && (
        <Section title="Why they fit">
          {recommendation.fit_reasons.map((reason, i) => (
            <li key={i} className="text-signal/90">
              {reason}
            </li>
          ))}
        </Section>
      )}

      {recommendation.top_risks.length > 0 && (
        <Section title="Watch for">
          {recommendation.top_risks.map((risk, i) => (
            <li key={i} className="text-amber/90">
              {risk}
            </li>
          ))}
        </Section>
      )}

      <div className="mt-6 pt-4 border-t border-ink-600">
        <p className="font-mono text-[10px] uppercase tracking-widest text-paper-faint mb-1">
          Suggested approach
        </p>
        <p className="text-sm text-paper leading-relaxed">{recommendation.suggested_approach}</p>
      </div>

      <div className="mt-4">
        <p className="font-mono text-[10px] uppercase tracking-widest text-paper-faint mb-1">
          Solution match
        </p>
        <p className="text-sm text-paper-faint italic">
          {recommendation.solution_match ?? "Not configured - awaiting the OxiQ offering catalog."}
        </p>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-4">
      <p className="font-mono text-[10px] uppercase tracking-widest text-paper-faint mb-1.5">{title}</p>
      <ul className="space-y-1 text-sm leading-relaxed list-disc list-inside">{children}</ul>
    </div>
  );
}

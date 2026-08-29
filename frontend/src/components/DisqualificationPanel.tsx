import { formatPercent } from "../lib/format";
import type { DisqualificationExplanation } from "../types";

const DECISION_CONFIG: Record<
  DisqualificationExplanation["final_decision"],
  { label: string; color: string; border: string }
> = {
  qualified: { label: "QUALIFIED", color: "text-signal", border: "border-signal" },
  disqualified: { label: "DISQUALIFIED", color: "text-rose", border: "border-rose" },
  insufficient_data: { label: "INSUFFICIENT DATA", color: "text-amber", border: "border-amber" },
};

export function DisqualificationPanel({
  disqualification,
}: {
  disqualification: DisqualificationExplanation;
}) {
  const config = DECISION_CONFIG[disqualification.final_decision];

  return (
    <div className={`border ${config.border} bg-ink-800 rounded-sm p-6`}>
      <div className="flex items-center justify-between mb-3">
        <span className={`font-mono text-xs uppercase tracking-widest font-semibold ${config.color}`}>
          {config.label}
        </span>
        <span className="font-mono text-[10px] text-paper-faint">
          {formatPercent(disqualification.confidence)} confidence
        </span>
      </div>

      <p className="text-sm text-paper-dim leading-relaxed mb-4">{disqualification.primary_reason}</p>

      {disqualification.secondary_reasons.length > 0 && (
        <ul className="space-y-1 mb-4">
          {disqualification.secondary_reasons.map((reason, i) => (
            <li key={i} className="text-[13px] text-paper-faint border-l-2 border-ink-600 pl-3">
              {reason}
            </li>
          ))}
        </ul>
      )}

      {disqualification.data_quality_limitations.length > 0 && (
        <div className="mb-4">
          <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-1.5">
            Data quality limitations
          </p>
          <ul className="space-y-1">
            {disqualification.data_quality_limitations.map((item, i) => (
              <li key={i} className="text-[13px] text-rose/80">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {disqualification.missing_evidence.length > 0 && (
        <div className="mb-4">
          <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-1.5">Missing evidence</p>
          <ul className="space-y-1">
            {disqualification.missing_evidence.map((item, i) => (
              <li key={i} className="text-[13px] text-paper-faint">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {disqualification.applied_adjustments.length > 0 && (
        <div className="mb-4">
          <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-1.5">
            Score adjustments applied
          </p>
          <ul className="space-y-1">
            {disqualification.applied_adjustments.map((item, i) => (
              <li key={i} className="text-[13px] text-amber/90">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {disqualification.supporting_evidence.length > 0 && (
        <div className="mb-4">
          <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-1.5">Supporting evidence</p>
          <ul className="space-y-1">
            {disqualification.supporting_evidence.map((item, i) => (
              <li key={i} className="text-[13px] text-paper-dim">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="pt-3 border-t border-ink-700">
        <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-1">Recommended next action</p>
        <p className="text-sm text-paper">{disqualification.recommended_next_action}</p>
      </div>
    </div>
  );
}

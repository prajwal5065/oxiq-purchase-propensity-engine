import type { CompanySummary } from "../types";

const DECISION_CONFIG: Record<
  NonNullable<CompanySummary["final_decision"]>,
  { label: string; color: string }
> = {
  qualified: { label: "QUALIFIED", color: "text-signal" },
  disqualified: { label: "DISQUALIFIED", color: "text-rose" },
  insufficient_data: { label: "INSUFFICIENT DATA", color: "text-amber" },
};

export function DecisionBadge({ decision }: { decision: CompanySummary["final_decision"] }) {
  if (!decision) {
    return <span className="font-mono text-[10px] uppercase tracking-wide text-paper-faint">Not analyzed</span>;
  }
  const config = DECISION_CONFIG[decision];
  return <span className={`font-mono text-[10px] uppercase tracking-wide ${config.color}`}>{config.label}</span>;
}

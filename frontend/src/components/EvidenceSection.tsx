import { useMemo, useState } from "react";
import { EvidenceCard } from "./EvidenceCard";
import type { AnalysisExplanation, EvidenceRecord } from "../types";

type Filter = "all" | "positive" | "negative" | "unlabeled";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "positive", label: "Positive" },
  { value: "negative", label: "Negative" },
  { value: "unlabeled", label: "Unlabeled" },
];

export function EvidenceSection({
  evidence,
  explanation,
}: {
  evidence: EvidenceRecord[];
  explanation: AnalysisExplanation | null;
}) {
  const [filter, setFilter] = useState<Filter>("all");

  const directionByEvidenceId = useMemo(() => {
    const map = new Map<string, "positive" | "negative">();
    for (const pillar of explanation?.pillar_explanations ?? []) {
      for (const c of pillar.positive_evidence) {
        if (c.evidence_id) map.set(c.evidence_id, "positive");
      }
      for (const c of pillar.negative_evidence) {
        if (c.evidence_id) map.set(c.evidence_id, "negative");
      }
    }
    return map;
  }, [explanation]);

  const filtered = evidence.filter((item) => {
    if (filter === "all") return true;
    const direction = directionByEvidenceId.get(item.id);
    if (filter === "unlabeled") return !direction;
    return direction === filter;
  });

  const notConfiguredOrFailed =
    explanation?.evidence_coverage.collector_statuses.filter(
      (s) => s.status === "not_configured" || s.status === "error" || s.status === "timeout" || s.status === "blocked",
    ) ?? [];

  const missingEvidence = explanation?.disqualification.missing_evidence ?? [];

  return (
    <div>
      {(missingEvidence.length > 0 || notConfiguredOrFailed.length > 0) && (
        <div className="grid sm:grid-cols-2 gap-3 mb-5">
          {missingEvidence.length > 0 && (
            <div className="border border-dashed border-ink-500 rounded-sm p-4">
              <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-2">
                Missing evidence
              </p>
              <ul className="space-y-1">
                {missingEvidence.map((item, i) => (
                  <li key={i} className="text-[13px] text-paper-faint">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {notConfiguredOrFailed.length > 0 && (
            <div className="border border-dashed border-ink-500 rounded-sm p-4">
              <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-2">
                Unavailable / failed sources
              </p>
              <ul className="space-y-1">
                {notConfiguredOrFailed.map((s) => (
                  <li key={s.source} className="text-[13px] text-paper-faint">
                    <span className="text-paper-dim">{s.source}</span> &mdash; {s.status.replace(/_/g, " ")}
                    {s.errors.length > 0 && `: ${s.errors[0]}`}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {evidence.length === 0 ? (
        <div className="border border-dashed border-ink-500 rounded-sm p-8 text-center">
          <p className="font-mono text-xs uppercase tracking-wider text-paper-faint mb-1">No evidence on file</p>
          <p className="text-sm text-paper-dim">
            Nothing was extracted for this company yet. This may mean sources returned nothing, or live
            collection/extraction is disabled.
          </p>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="flex gap-1">
              {FILTERS.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setFilter(f.value)}
                  className={`font-mono text-[10px] uppercase tracking-wide px-2 py-1 rounded-sm border transition-colors ${
                    filter === f.value
                      ? "border-signal text-signal"
                      : "border-ink-600 text-paper-faint hover:text-paper-dim"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <span className="font-mono text-[10px] text-paper-faint">
              {filtered.length} of {evidence.length}
            </span>
          </div>

          {filtered.length === 0 ? (
            <p className="font-mono text-xs text-paper-faint text-center py-6">
              No evidence matches this filter.
            </p>
          ) : (
            <div className="grid sm:grid-cols-2 gap-3">
              {filtered.map((item) => (
                <EvidenceCard key={item.id} evidence={item} direction={directionByEvidenceId.get(item.id)} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

import { PILLAR_LABELS, type PillarScore } from "../types";

function splitReason(reason: string): { label: string; body: string } {
  const idx = reason.indexOf(":");
  if (idx === -1) return { label: "", body: reason };
  return { label: reason.slice(0, idx).trim(), body: reason.slice(idx + 1).trim() };
}

export function EvidenceLog({ pillars }: { pillars: PillarScore[] }) {
  const withEvidence = pillars.filter((p) => p.reasons.length > 0);

  if (withEvidence.length === 0) {
    return (
      <div className="border border-dashed border-ink-500 rounded-sm p-6 text-center">
        <p className="font-mono text-xs uppercase tracking-wider text-paper-faint">
          No evidence on file
        </p>
        <p className="mt-2 text-sm text-paper-dim">
          Nothing matched across any pillar. Re-run once live collectors are enabled.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {withEvidence.map((pillar) => (
        <div key={pillar.score_type}>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-mono text-[10px] uppercase tracking-widest text-signal">
              {PILLAR_LABELS[pillar.score_type] ?? pillar.score_type}
            </span>
            <span className="h-px flex-1 bg-ink-600" />
            <span className="font-mono text-[10px] text-paper-faint">
              {pillar.reasons.length} signal{pillar.reasons.length === 1 ? "" : "s"}
            </span>
          </div>
          <ul className="space-y-2">
            {pillar.reasons.map((reason, i) => {
              const { label, body } = splitReason(reason);
              return (
                <li
                  key={i}
                  className="border-l-2 border-ink-500 pl-3 py-0.5 text-sm text-paper-dim leading-relaxed"
                >
                  {label && (
                    <span className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mr-2">
                      {label}
                    </span>
                  )}
                  <span className="italic">&ldquo;{body}&rdquo;</span>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}

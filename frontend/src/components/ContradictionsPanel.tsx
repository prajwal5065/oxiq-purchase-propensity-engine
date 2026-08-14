import type { ContradictionEvidenceRef, ContradictionFinding, ContradictionReport } from "../types";

const SEVERITY_COLOR: Record<string, string> = {
  high: "text-rose",
  medium: "text-amber",
};

function EvidenceRefBlock({ label, ref }: { label: string; ref: ContradictionEvidenceRef }) {
  return (
    <div className="flex-1 min-w-0">
      <p className="font-mono text-[10px] uppercase tracking-wide text-paper-faint mb-1">{label}</p>
      <p className="text-sm text-paper-dim italic leading-relaxed">&ldquo;{ref.excerpt}&rdquo;</p>
      <p className="font-mono text-[10px] text-paper-faint mt-1">{ref.source}</p>
    </div>
  );
}

function FindingCard({ finding }: { finding: ContradictionFinding }) {
  return (
    <div className="border border-ink-600 rounded-sm p-4 bg-ink-900">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-[10px] uppercase tracking-wide text-paper">{finding.theme}</span>
        <span className={`font-mono text-[10px] uppercase tracking-widest font-semibold ${SEVERITY_COLOR[finding.severity]}`}>
          {finding.severity} severity
        </span>
      </div>
      <p className="text-sm text-paper-dim leading-relaxed mb-3">{finding.description}</p>
      <div className="flex flex-col sm:flex-row gap-4">
        <EvidenceRefBlock label="Evidence A" ref={finding.evidence_a} />
        <div className="hidden sm:block w-px bg-ink-700" />
        <EvidenceRefBlock label="Evidence B" ref={finding.evidence_b} />
      </div>
    </div>
  );
}

export function ContradictionsPanel({ contradictions }: { contradictions: ContradictionReport }) {
  return (
    <div
      className={`border ${contradictions.has_contradictions ? "border-amber" : "border-ink-600"} bg-ink-800 rounded-sm p-6`}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint">Contradictions</h3>
        <span
          className={`font-mono text-xs uppercase tracking-widest font-semibold ${
            contradictions.has_contradictions ? "text-amber" : "text-signal"
          }`}
        >
          {contradictions.has_contradictions ? `${contradictions.findings.length} FOUND` : "NONE FOUND"}
        </span>
      </div>

      <p className="text-sm text-paper-dim leading-relaxed mb-4">{contradictions.summary}</p>

      {contradictions.findings.length > 0 && (
        <div className="space-y-3">
          {contradictions.findings.map((finding, i) => (
            <FindingCard key={i} finding={finding} />
          ))}
        </div>
      )}
    </div>
  );
}

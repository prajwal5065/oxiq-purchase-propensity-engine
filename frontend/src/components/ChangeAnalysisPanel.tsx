import type { DecisionChangeAnalysis } from "../types";

export function ChangeAnalysisPanel({ changeAnalysis }: { changeAnalysis: DecisionChangeAnalysis }) {
  if (changeAnalysis.factors.length === 0) {
    return null;
  }

  return (
    <div className="border border-ink-600 bg-ink-800 rounded-sm p-6">
      <h3 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint mb-3">
        What Would Change This Decision
      </h3>
      <p className="text-sm text-paper-dim leading-relaxed mb-4">{changeAnalysis.summary}</p>

      <ul className="space-y-3">
        {changeAnalysis.factors.map((factor, i) => (
          <li key={i} className="border-l-2 border-ink-600 pl-3 py-0.5">
            <p className="text-sm text-paper leading-relaxed">{factor.description}</p>
            {factor.evidence_needed.length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {factor.evidence_needed.map((need, j) => (
                  <span
                    key={j}
                    className="font-mono text-[10px] text-paper-faint border border-dashed border-ink-600 rounded-sm px-1.5 py-0.5"
                  >
                    {need}
                  </span>
                ))}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

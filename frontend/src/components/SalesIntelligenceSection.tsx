import type { ReactNode } from "react";
import { formatPercent } from "../lib/format";
import type { SalesIntelligence, SalesRisk } from "../types";

const RISK_LABEL: Record<SalesRisk["risk_type"], string> = {
  contradiction: "Contradiction",
  missing_evidence: "Missing Evidence",
  existing_vendor: "Existing Vendor",
  other: "Other",
};

const RISK_COLOR: Record<SalesRisk["risk_type"], string> = {
  contradiction: "text-rose",
  missing_evidence: "text-amber",
  existing_vendor: "text-amber",
  other: "text-paper-faint",
};

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="border border-ink-600 bg-ink-800 rounded-sm p-6">
      <h3 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint mb-3">{title}</h3>
      {children}
    </div>
  );
}

export function SalesIntelligenceSection({ sales }: { sales: SalesIntelligence | null }) {
  if (sales === null) {
    return (
      <div className="border border-dashed border-ink-500 rounded-sm p-8 text-center">
        <p className="font-mono text-xs uppercase tracking-wider text-paper-faint mb-1">
          Sales Intelligence unavailable
        </p>
        <p className="text-sm text-paper-dim max-w-md mx-auto">
          This analysis predates the Sales Intelligence feature, or ran in stub mode. Re-run the analysis
          to generate it.
        </p>
      </div>
    );
  }

  if (!sales.data_sufficient) {
    return (
      <div className="border border-amber rounded-sm p-8 text-center bg-ink-800">
        <p className="font-mono text-xs uppercase tracking-wider text-amber mb-1">Insufficient Data</p>
        <p className="text-sm text-paper-dim max-w-md mx-auto">
          There isn&rsquo;t enough evidence to make a reliable sales assertion for this company yet. This
          is a data gap, not a negative signal.
        </p>
      </div>
    );
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <Card title="Opportunity">
        {sales.opportunity ? (
          <>
            <p className="text-sm text-paper leading-relaxed mb-2">{sales.opportunity.description}</p>
            <p className="font-mono text-[10px] text-paper-faint">
              {formatPercent(sales.opportunity.confidence)} confidence
            </p>
          </>
        ) : (
          <p className="text-sm text-paper-faint italic">No opportunity identified from current evidence.</p>
        )}
      </Card>

      <Card title="Solution Fit">
        {sales.solution_fit ? (
          <>
            <p className="font-mono text-xs uppercase tracking-wide text-signal mb-2">
              {sales.solution_fit.use_case}
            </p>
            <p className="text-sm text-paper-dim leading-relaxed mb-2">{sales.solution_fit.fit_reasoning}</p>
            <p className="font-mono text-[10px] text-paper-faint">
              {formatPercent(sales.solution_fit.confidence)} confidence
            </p>
          </>
        ) : (
          <p className="text-sm text-paper-faint italic">No solution fit identified from current evidence.</p>
        )}
      </Card>

      <Card title="Likely Buyer Roles">
        {sales.likely_buyer_roles.length > 0 ? (
          <ul className="space-y-2">
            {sales.likely_buyer_roles.map((role, i) => (
              <li key={i} className="border-l-2 border-ink-600 pl-3 py-0.5">
                <p className="font-mono text-xs text-paper">{role.role_title}</p>
                <p className="text-sm text-paper-dim leading-relaxed">{role.rationale}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-paper-faint italic">No buyer roles surfaced from current evidence.</p>
        )}
      </Card>

      <Card title="Sales Trigger">
        {sales.sales_trigger ? (
          <>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-[10px] uppercase tracking-wide text-signal">
                {sales.sales_trigger.trigger_type.replace(/_/g, " ")}
              </span>
              <span className="font-mono text-[10px] uppercase tracking-wide text-paper-faint">
                {sales.sales_trigger.freshness_label.replace(/_/g, " ")}
              </span>
            </div>
            <p className="text-sm text-paper-dim italic leading-relaxed mb-2">
              &ldquo;{sales.sales_trigger.excerpt}&rdquo;{" "}
              <span className="not-italic text-paper-faint">&mdash; {sales.sales_trigger.source}</span>
            </p>
            <p className="text-sm text-paper leading-relaxed">{sales.sales_trigger.narrative}</p>
          </>
        ) : (
          <p className="text-sm text-paper-faint italic">No timing trigger identified.</p>
        )}
      </Card>

      <Card title="Sales Risks">
        {sales.risks.length > 0 ? (
          <ul className="space-y-2">
            {sales.risks.map((risk, i) => (
              <li key={i} className="border-l-2 border-ink-600 pl-3 py-0.5">
                <span className={`font-mono text-[10px] uppercase tracking-wide ${RISK_COLOR[risk.risk_type]}`}>
                  {RISK_LABEL[risk.risk_type]}
                </span>
                <p className="text-sm text-paper-dim leading-relaxed">{risk.description}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-paper-faint italic">No risks identified from current evidence.</p>
        )}
      </Card>

      <Card title="Recommended Next Action">
        {sales.recommended_next_action ? (
          <>
            <p className="text-sm text-paper leading-relaxed mb-2">{sales.recommended_next_action.action}</p>
            <p className="text-sm text-paper-dim leading-relaxed">{sales.recommended_next_action.rationale}</p>
          </>
        ) : (
          <p className="text-sm text-paper-faint italic">No next action generated from current evidence.</p>
        )}
      </Card>
    </div>
  );
}

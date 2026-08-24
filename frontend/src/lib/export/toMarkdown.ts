import type { ReportData } from "./reportData";

function section(title: string): string {
  return `\n## ${title}\n`;
}

export function reportToMarkdown(data: ReportData): string {
  const lines: string[] = [];

  lines.push(`# ${data.company.name} — OxiQ Purchase Propensity Report`);
  lines.push(`*Generated ${new Date(data.generatedAt).toLocaleString()}*`);

  lines.push(section("Company"));
  lines.push(`- **Domain:** ${data.company.domain}`);
  if (data.company.industry) lines.push(`- **Industry:** ${data.company.industry}`);
  lines.push(`- **Last processed:** ${data.company.lastProcessed}`);

  lines.push(section("Final Decision"));
  if (data.decision.headline) lines.push(`> ${data.decision.headline}`);
  lines.push(`- **Priority:** ${data.decision.priorityLabel}`);
  lines.push(`- **Decision:** ${data.decision.finalDecision}`);
  lines.push(`- **Purchase score:** ${data.decision.purchaseScore} / 100`);
  lines.push(`- **Confidence:** ${data.decision.purchaseConfidence}`);
  if (data.decision.primaryReason) {
    lines.push(`- **Primary reason:** ${data.decision.primaryReason}`);
  }
  for (const reason of data.decision.secondaryReasons) {
    lines.push(`  - ${reason}`);
  }

  if (data.confidence) {
    lines.push(section("Confidence"));
    lines.push(`${data.confidence.summary} (${data.confidence.overall}, ${data.confidence.level})`);
    for (const f of data.confidence.factors) {
      lines.push(`- **${f.name}** — ${f.value} (weight ${f.weight}): ${f.description}`);
    }
  }

  lines.push(section("Pillar Scores"));
  for (const p of data.pillars) {
    lines.push(`### ${p.name} — ${p.score}/100 (${p.confidence} confidence)`);
    for (const reason of p.reasons) lines.push(`- ${reason}`);
  }

  if (data.decisionIntelligence) {
    const di = data.decisionIntelligence;
    lines.push(section("Decision Intelligence"));

    lines.push(`### Buying Intent — ${di.buyingIntentLevel}`);
    lines.push(di.buyingIntentRationale);
    for (const s of di.buyingIntentSignals) {
      lines.push(`- [${s.strength}] "${s.excerpt}" — ${s.source}`);
    }

    lines.push(`\n### Why Now`);
    lines.push(di.whyNowNarrative);
    for (const t of di.whyNowTriggers) {
      lines.push(`- [${t.triggerType}, ${t.freshness}] "${t.excerpt}" — ${t.source}`);
    }

    lines.push(`\n### Contradictions`);
    lines.push(di.contradictionsSummary);
    for (const c of di.contradictions) {
      lines.push(`- **${c.theme}** (${c.severity} severity): ${c.description}`);
      lines.push(`  - A: ${c.evidenceA}`);
      lines.push(`  - B: ${c.evidenceB}`);
    }

    lines.push(`\n### What Would Change This Decision`);
    lines.push(di.changeSummary);
    for (const f of di.changeFactors) {
      lines.push(`- ${f.description}${f.evidenceNeeded.length ? ` (needs: ${f.evidenceNeeded.join(", ")})` : ""}`);
    }
  }

  if (data.salesIntelligence) {
    const si = data.salesIntelligence;
    lines.push(section("Sales Intelligence"));
    if (!si.dataSufficient) {
      lines.push("*Insufficient data for a reliable sales assertion.*");
    } else {
      if (si.opportunity) lines.push(`**Opportunity:** ${si.opportunity}`);
      if (si.solutionFitUseCase) {
        lines.push(`**Solution fit:** ${si.solutionFitUseCase} — ${si.solutionFitReasoning}`);
      }
      if (si.buyerRoles.length) {
        lines.push(`\n**Likely buyer roles:**`);
        for (const r of si.buyerRoles) lines.push(`- ${r.title}: ${r.rationale}`);
      }
      if (si.salesTriggerNarrative) lines.push(`\n**Sales trigger:** ${si.salesTriggerNarrative}`);
      if (si.risks.length) {
        lines.push(`\n**Risks:**`);
        for (const r of si.risks) lines.push(`- [${r.type}] ${r.description}`);
      }
      if (si.nextAction) {
        lines.push(`\n**Recommended next action:** ${si.nextAction}`);
        if (si.nextActionRationale) lines.push(si.nextActionRationale);
      }
    }
  }

  lines.push(section(`Evidence (${data.evidence.length})`));
  for (const e of data.evidence) {
    lines.push(`- **${e.label}** [${e.category}, ${e.confidence} confidence, ${e.date}]`);
    lines.push(`  "${e.excerpt}" — ${e.source}${e.url ? ` (${e.url})` : ""}`);
  }

  if (data.sources.length) {
    lines.push(section("Sources / Collector Status"));
    for (const s of data.sources) {
      lines.push(`- ${s.source}: ${s.status} (${s.signalCount} signals)`);
    }
  }

  return lines.join("\n");
}

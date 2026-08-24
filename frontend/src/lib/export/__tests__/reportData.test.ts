import { describe, expect, it } from "vitest";
import { buildReportData } from "../reportData";
import { reportToMarkdown } from "../toMarkdown";
import { buildJsonExport, reportToJsonString } from "../toJson";
import { sampleDossier } from "./fixtures";

describe("buildReportData", () => {
  const report = buildReportData(sampleDossier);

  it("carries over company details", () => {
    expect(report.company.name).toBe("Acme Robotics");
    expect(report.company.domain).toBe("acme-robotics.com");
    expect(report.company.industry).toBe("Industrial Automation");
  });

  it("derives the final decision from the explanation, not a heuristic, when available", () => {
    expect(report.decision.disqualified).toBe(false);
    expect(report.decision.finalDecision).toBe("Qualified");
    expect(report.decision.purchaseScore).toBe("72");
    expect(report.decision.purchaseConfidence).toBe("81%");
    expect(report.decision.headline).toContain("Strong fit");
  });

  it("maps all six pillars with human-readable names", () => {
    expect(report.pillars).toHaveLength(6);
    expect(report.pillars.map((p) => p.name)).toContain("Digital Maturity");
    const need = report.pillars.find((p) => p.name === "Need");
    expect(need?.score).toBe("80");
    expect(need?.reasons).toContain("Hiring for ML roles");
  });

  it("includes decision intelligence: buying intent, why now, contradictions, change analysis", () => {
    expect(report.decisionIntelligence).not.toBeNull();
    expect(report.decisionIntelligence?.buyingIntentLevel).toBe("Strong");
    expect(report.decisionIntelligence?.whyNowTriggers).toHaveLength(1);
    expect(report.decisionIntelligence?.contradictions).toHaveLength(1);
    expect(report.decisionIntelligence?.contradictions[0].theme).toBe("Vendor status");
    expect(report.decisionIntelligence?.changeFactors).toHaveLength(1);
  });

  it("includes sales intelligence: opportunity, solution fit, buyer roles, trigger, risks, next action", () => {
    const si = report.salesIntelligence;
    expect(si).not.toBeNull();
    expect(si?.dataSufficient).toBe(true);
    expect(si?.opportunity).toContain("Modernizing");
    expect(si?.solutionFitUseCase).toBe("ML Ops platform");
    expect(si?.buyerRoles).toHaveLength(1);
    expect(si?.buyerRoles[0].title).toBe("VP Engineering");
    expect(si?.risks).toHaveLength(1);
    expect(si?.nextAction).toContain("discovery call");
  });

  it("includes evidence with source, url, date, confidence, category", () => {
    expect(report.evidence).toHaveLength(1);
    const item = report.evidence[0];
    expect(item.source).toBe("Greenhouse");
    expect(item.url).toBe("https://boards.greenhouse.io/acme/jobs/1");
    expect(item.confidence).toBe("90%");
    expect(item.category).toBe("AI/ML Hiring");
  });

  it("includes source/collector status", () => {
    expect(report.sources).toHaveLength(2);
    expect(report.sources.map((s) => s.source)).toEqual(["jobs", "tech"]);
  });

  it("falls back to a score-based priority when there's no explanation", () => {
    const noExplanation = buildReportData({ ...sampleDossier, explanation: null });
    expect(noExplanation.decisionIntelligence).toBeNull();
    expect(noExplanation.salesIntelligence).toBeNull();
    expect(noExplanation.decision.priorityLabel).toBe("High Priority"); // score 72 >= 70
    expect(noExplanation.decision.finalDecision).toBe("Unknown");
  });

  it("treats insufficient_data the same as disqualified for priority purposes", () => {
    const insufficientDossier = {
      ...sampleDossier,
      explanation: {
        ...sampleDossier.explanation!,
        disqualification: {
          ...sampleDossier.explanation!.disqualification,
          final_decision: "insufficient_data" as const,
        },
      },
    };
    const report2 = buildReportData(insufficientDossier);
    expect(report2.decision.disqualified).toBe(true);
  });
});

describe("reportToMarkdown", () => {
  const markdown = reportToMarkdown(buildReportData(sampleDossier));

  it("is plain text/markdown, not HTML", () => {
    expect(markdown).not.toContain("<div");
    expect(markdown).not.toContain("<span");
    expect(markdown).not.toContain("background");
    expect(markdown).not.toContain("style=");
  });

  it("includes the company name as a heading", () => {
    expect(markdown).toContain("# Acme Robotics");
  });

  it("includes every required dossier section", () => {
    for (const heading of [
      "## Company",
      "## Final Decision",
      "## Confidence",
      "## Pillar Scores",
      "## Decision Intelligence",
      "## Sales Intelligence",
      "## Evidence",
      "## Sources",
    ]) {
      expect(markdown).toContain(heading);
    }
  });

  it("includes the evidence excerpt and source", () => {
    expect(markdown).toContain("Hiring 3 ML engineers");
    expect(markdown).toContain("Greenhouse");
  });

  it("includes the recommended next action", () => {
    expect(markdown).toContain("Schedule a discovery call with VP Engineering.");
  });
});

describe("JSON export", () => {
  it("preserves the complete structured result, not a flattened/relabeled version", () => {
    const exported = buildJsonExport(sampleDossier);
    // Raw enum values, IDs, and nested objects survive untouched.
    expect(exported.explanation?.decision_intelligence.recommendation.priority).toBe("high_priority");
    expect(exported.explanation?.sales_intelligence?.evidence_ids).toEqual(["e1", "e2", "e3", "e4"]);
    expect(exported.evidence[0].job_ats_provider).toBe("greenhouse");
    expect(exported.scores.pillars).toHaveLength(6);
    expect(exported.company.id).toBe("c1");
  });

  it("produces valid, parseable JSON with an exported_at timestamp", () => {
    const jsonString = reportToJsonString(sampleDossier);
    const parsed = JSON.parse(jsonString);
    expect(parsed.exported_at).toBeTruthy();
    expect(parsed.company.domain).toBe("acme-robotics.com");
  });

  it("handles a null explanation without throwing", () => {
    const jsonString = reportToJsonString({ ...sampleDossier, explanation: null });
    const parsed = JSON.parse(jsonString);
    expect(parsed.explanation).toBeNull();
  });
});

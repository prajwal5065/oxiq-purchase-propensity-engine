import { CompanyList } from "../components/CompanyList";
import { IntakeConsole } from "../components/IntakeConsole";
import { PortfolioIntelligencePanel } from "../components/PortfolioIntelligencePanel";
import { PortfolioSummaryBar } from "../components/PortfolioSummaryBar";

export function DashboardPage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-10">
      <IntakeConsole />
      <PortfolioSummaryBar />
      <PortfolioIntelligencePanel />
      <CompanyList />
    </div>
  );
}

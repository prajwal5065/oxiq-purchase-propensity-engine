import { Route, Routes } from "react-router-dom";
import { Header } from "./components/Header";
import { CompanyPage } from "./pages/CompanyPage";
import { DashboardPage } from "./pages/DashboardPage";

export function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/company/:id" element={<CompanyPage />} />
        </Routes>
      </main>
      <footer className="border-t border-ink-600 py-6">
        <p className="max-w-5xl mx-auto px-6 font-mono text-[10px] uppercase tracking-widest text-paper-faint">
          OxiQ &mdash; not a chatbot, not a CRM. A propensity engine.
        </p>
      </footer>
    </div>
  );
}

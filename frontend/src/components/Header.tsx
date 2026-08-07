import { Link } from "react-router-dom";

export function Header() {
  return (
    <header className="border-b border-ink-600">
      <div className="max-w-5xl mx-auto px-6 py-5 flex items-center justify-between">
        <Link to="/" className="flex items-baseline gap-3 group">
          <span className="font-display text-xl font-semibold text-paper tracking-tight">
            OxiQ
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-signal">
            Propensity Engine
          </span>
        </Link>
        <span className="font-mono text-[10px] uppercase tracking-widest text-paper-faint hidden sm:block">
          Evidence-backed. No guesses.
        </span>
      </div>
    </header>
  );
}

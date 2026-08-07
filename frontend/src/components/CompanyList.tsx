import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { formatRelativeDate } from "../lib/format";
import type { CompanySummary } from "../types";

const PAGE_SIZE = 10;

export function CompanyList() {
  const [items, setItems] = useState<CompanySummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .listCompanies({ limit: PAGE_SIZE, offset })
      .then((res) => {
        if (cancelled) return;
        setItems((prev) => (offset === 0 ? res.items : [...prev, ...res.items]));
        setTotal(res.total);
        setError(null);
      })
      .catch(() => !cancelled && setError("Couldn't load the dossier index."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [offset]);

  if (error) {
    return <p className="font-mono text-xs text-rose">{error}</p>;
  }

  if (!loading && items.length === 0) {
    return (
      <div className="border border-dashed border-ink-500 rounded-sm p-10 text-center">
        <p className="font-mono text-xs uppercase tracking-wider text-paper-faint mb-1">
          No dossiers yet
        </p>
        <p className="text-sm text-paper-dim">Run an intake above to open the first one.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-mono text-[10px] uppercase tracking-widest text-paper-faint">
          Dossier index
        </h2>
        <span className="font-mono text-[10px] text-paper-faint">{total} on file</span>
      </div>

      <ul className="divide-y divide-ink-600 border border-ink-600 rounded-sm">
        {items.map((company) => (
          <li key={company.id}>
            <Link
              to={`/company/${company.id}`}
              className="flex items-center justify-between px-4 py-3 hover:bg-ink-700 transition-colors group"
            >
              <div className="min-w-0">
                <p className="text-sm text-paper truncate group-hover:text-signal transition-colors">
                  {company.name}
                </p>
                <p className="font-mono text-xs text-paper-faint truncate">{company.domain}</p>
              </div>
              <div className="flex items-center gap-4 shrink-0 ml-4">
                {company.industry && (
                  <span className="font-mono text-[10px] uppercase tracking-wide text-paper-dim hidden sm:block">
                    {company.industry}
                  </span>
                )}
                <span className="font-mono text-[10px] text-paper-faint">
                  {formatRelativeDate(company.last_processed_at)}
                </span>
              </div>
            </Link>
          </li>
        ))}
      </ul>

      {items.length < total && (
        <button
          onClick={() => setOffset(items.length)}
          disabled={loading}
          className="mt-3 w-full font-mono text-xs uppercase tracking-widest text-paper-dim border border-ink-600 rounded-sm py-2 hover:border-signal hover:text-signal transition-colors disabled:opacity-50"
        >
          {loading ? "Loading\u2026" : "Load more"}
        </button>
      )}
    </div>
  );
}

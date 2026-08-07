import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { JobStatus } from "../types";

const POLL_INTERVAL_MS = 2000;

type ConsoleState =
  | { phase: "idle" }
  | { phase: "queued"; jobId: string; status: JobStatus }
  | { phase: "error"; message: string };

export function IntakeConsole() {
  const [domain, setDomain] = useState("");
  const [state, setState] = useState<ConsoleState>({ phase: "idle" });
  const navigate = useNavigate();
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = domain.trim().replace(/^https?:\/\//, "").replace(/\/$/, "");
    if (!cleaned) return;

    try {
      const job = await api.submitAnalysis(cleaned);
      setState({ phase: "queued", jobId: job.job_id, status: job.status });

      pollRef.current = window.setInterval(async () => {
        try {
          const status = await api.getJobStatus(job.job_id);
          if (status.status === "completed" && status.company_id) {
            if (pollRef.current) window.clearInterval(pollRef.current);
            navigate(`/company/${status.company_id}`);
          } else if (status.status === "failed") {
            if (pollRef.current) window.clearInterval(pollRef.current);
            setState({ phase: "error", message: status.error_message ?? "Analysis failed." });
          } else {
            setState({ phase: "queued", jobId: job.job_id, status: status.status });
          }
        } catch (err) {
          if (pollRef.current) window.clearInterval(pollRef.current);
          setState({ phase: "error", message: describeError(err) });
        }
      }, POLL_INTERVAL_MS);
    } catch (err) {
      setState({ phase: "error", message: describeError(err) });
    }
  };

  const isBusy = state.phase === "queued";

  return (
    <div className="relative border border-ink-600 bg-ink-800 rounded-sm px-6 py-8 sm:px-10 sm:py-10 overflow-hidden">
      <div className="absolute inset-0 bg-grid-fade pointer-events-none" />
      <div className="relative">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-signal mb-3">
          Intake &mdash; new dossier
        </p>
        <h1 className="font-display text-3xl sm:text-4xl text-paper leading-tight mb-3">
          Point it at a domain.
          <br />
          It builds the case.
        </h1>
        <p className="text-paper-dim text-sm max-w-md mb-6">
          Public signals in, a scored verdict out &mdash; every pillar cites the evidence it's built on.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="acme.com"
            disabled={isBusy}
            className="flex-1 bg-ink-900 border border-ink-500 rounded-sm px-4 py-3 font-mono text-sm text-paper placeholder:text-paper-faint focus:border-signal disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isBusy || !domain.trim()}
            className="bg-signal text-ink-900 font-mono text-xs uppercase tracking-widest font-semibold px-6 py-3 rounded-sm hover:bg-signal-glow transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isBusy ? "Scanning\u2026" : "Open dossier"}
          </button>
        </form>

        {state.phase === "queued" && (
          <div className="mt-5 flex items-center gap-2 font-mono text-xs text-signal">
            <span className="relative flex h-2 w-2">
              <span className="animate-pulse-glow absolute inline-flex h-full w-full rounded-full bg-signal opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-signal" />
            </span>
            {state.status === "pending" ? "queued for collection" : "gathering public signals\u2026"}
          </div>
        )}

        {state.phase === "error" && (
          <p className="mt-5 font-mono text-xs text-rose">{state.message}</p>
        )}
      </div>
    </div>
  );
}

function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    return err.status === 0
      ? "Can't reach the API. Is the backend running?"
      : `Request failed (${err.status}): ${err.message}`;
  }
  return "Something went wrong submitting this domain.";
}

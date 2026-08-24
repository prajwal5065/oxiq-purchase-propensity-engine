import { useEffect, useRef, useState } from "react";
import { exportReport } from "../lib/export";
import type { DossierData, ExportFormat } from "../lib/export";

const OPTIONS: { format: ExportFormat; label: string }[] = [
  { format: "docx", label: "Word (.docx)" },
  { format: "pdf", label: "PDF (.pdf)" },
  { format: "json", label: "JSON (.json)" },
  { format: "copy", label: "Copy Markdown / Text" },
];

export function ExportReportButton({ dossier }: { dossier: DossierData }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEscape);
    };
  }, [open]);

  const handleSelect = async (format: ExportFormat) => {
    setBusy(format);
    setError(null);
    try {
      await exportReport(format, dossier);
      if (format === "copy") {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
      setOpen(false);
    } catch {
      setError("Export failed — try again.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="relative" ref={rootRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-paper-dim border border-ink-600 rounded-sm px-3 py-1.5 hover:text-signal hover:border-signal transition-colors"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        {copied ? "Copied" : "Export Report"}
        <span className="text-paper-faint">{open ? "\u25b4" : "\u25be"}</span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-1 w-56 border border-ink-600 bg-ink-800 rounded-sm shadow-lg z-20 overflow-hidden"
        >
          {OPTIONS.map((opt) => (
            <button
              key={opt.format}
              role="menuitem"
              disabled={busy !== null}
              onClick={() => handleSelect(opt.format)}
              className="w-full text-left px-3 py-2 font-mono text-[11px] text-paper-dim hover:bg-ink-700 hover:text-signal transition-colors disabled:opacity-50 disabled:cursor-wait"
            >
              {busy === opt.format ? "Generating\u2026" : opt.label}
            </button>
          ))}
        </div>
      )}

      {error && <p className="absolute right-0 mt-1 font-mono text-[10px] text-rose whitespace-nowrap">{error}</p>}
    </div>
  );
}

"use client";

import { LoaderCircle } from "lucide-react";
import Link from "next/link";
import { ProviderCapability, SyncJob } from "@/lib/context-sync/types";

function remainingLabel(seconds?: number | null) {
  if (seconds == null || seconds < 1) return null;
  if (seconds < 60) return "Less than a minute remaining";
  const minutes = Math.max(1, Math.ceil(seconds / 60));
  return `About ${minutes} ${minutes === 1 ? "minute" : "minutes"} remaining`;
}

export function SyncProgress({
  provider,
  job,
  busy,
  error,
  onRetry,
}: {
  provider: ProviderCapability | null;
  job: SyncJob | null;
  busy: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  const percent = Math.max(0, Math.min(100, Number(job?.percent || 0)));
  const remaining = remainingLabel(job?.estimated_seconds_remaining);
  const status = error || job?.display_message || "Securely connecting";

  return (
    <section className="mx-auto flex min-h-[52vh] w-full max-w-xl flex-col items-center justify-center text-center" aria-live="polite">
      <div className="relative grid h-20 w-20 place-items-center rounded-full border border-primary/20 bg-card shadow-[0_20px_55px_rgba(18,70,52,0.13)]">
        <LoaderCircle className="animate-spin text-primary" size={30} />
        <span className="absolute inset-[-8px] rounded-full border border-accent-gold/20" />
      </div>

      <p className="mt-7 text-xs font-semibold uppercase tracking-[0.16em] text-primary">{provider?.display_name || "AI context"}</p>
      <h1 className="display-type mt-2 text-3xl font-semibold sm:text-4xl">Bringing your context into Muslim LLM</h1>
      <p className={`mt-4 min-h-6 text-sm ${error ? "text-red-700 dark:text-red-300" : "text-muted-foreground"}`}>{status}</p>

      {!error ? (
        <div className="mt-8 w-full">
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${Math.max(percent, busy ? 7 : 2)}%` }} />
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
            <span>{Math.round(percent)}%</span>
            <span>{remaining || "You may close this page. Sync will continue."}</span>
          </div>
        </div>
      ) : null}

      {error ? (
        <button className="mt-5 text-sm font-semibold text-primary underline-offset-4 hover:underline" onClick={onRetry} type="button">Try again</button>
      ) : null}
      {!error && job?.ready_for_use ? (
        <Link className="mt-5 text-sm font-semibold text-primary underline-offset-4 hover:underline" href={job.entry_chat_id ? `/?chat=${job.entry_chat_id}` : "/"}>
          Open Muslim LLM
        </Link>
      ) : null}
    </section>
  );
}

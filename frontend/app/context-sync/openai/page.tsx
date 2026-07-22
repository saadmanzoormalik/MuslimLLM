"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, FolderSearch, Import, LoaderCircle, LockKeyhole, RotateCcw, X } from "lucide-react";
import { API_BASE, apiGet, apiPost } from "@/lib/api";
import { createId } from "@/lib/id";

type TransferSession = {
  session_id: string;
  job_id?: string | null;
  state: string;
  stage: string;
  status: string;
  display_message: string;
  progress_percent: number;
  processed_items: number;
  total_items: number;
  estimated_seconds_remaining?: number | null;
  chats_restored: number;
  projects_restored: number;
  files_restored: number;
  ready_for_use: boolean;
  background_sync_continues: boolean;
  latest_chat_id?: string | null;
  available_chat_count: number;
  transfer_method?: string | null;
  sync_duration_seconds?: number | null;
  recoverable: boolean;
  next_action: "grant_folder_access" | "select_file" | "resume" | "continue" | "sync";
};

type AgreeResult = {
  session_id: string;
  next_action: "open_official_export" | "sync";
  action_url: string;
  display_message: string;
};

type ValidationReport = {
  validation_status: "passed" | "passed_with_exceptions" | "failed";
  conversations_imported: number;
  projects_transferred: number;
  files_imported: number;
  duplicates_prevented: number;
  continuity_validations_passed: number;
  continuity_validations_run: number;
  sync_duration_seconds: number;
  exceptions: Array<{ user_message?: string; error_class?: string; source_object_id?: string }>;
};

type TransferReportResult = {
  report: ValidationReport | null;
};

const SESSION_KEY = "muslim_llm_openai_transfer_session";
const DEVICE_KEY = "muslim_llm_local_device_id";
const COMPLETE_STATES = new Set(["completed", "completed_with_exceptions"]);
const OFFICIAL_EXPORT_URL = "https://help.openai.com/en/articles/7260999-how-do-i-export-my-data";

function etaLabel(seconds?: number | null) {
  if (!seconds || seconds < 1) return null;
  if (seconds < 60) return "Less than a minute";
  return `About ${Math.ceil(seconds / 60)} min`;
}

function durationLabel(seconds?: number | null) {
  if (seconds == null) return "Pending";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return remaining ? `${minutes}m ${remaining}s` : `${minutes}m`;
}

function localDeviceId() {
  const stored = window.localStorage.getItem(DEVICE_KEY);
  if (stored) return stored;
  const created = createId();
  window.localStorage.setItem(DEVICE_KEY, created);
  return created;
}

export default function OpenAIContextSyncPage() {
  const fileInput = useRef<HTMLInputElement>(null);
  const [accepted, setAccepted] = useState(false);
  const [session, setSession] = useState<TransferSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [report, setReport] = useState<ValidationReport | null>(null);
  const notified = useRef(false);

  useEffect(() => {
    const sessionId = window.localStorage.getItem(SESSION_KEY);
    if (!sessionId) return;
    apiGet<TransferSession>(`/context-sync/openai/session/${sessionId}`)
      .then(setSession)
      .catch(() => window.localStorage.removeItem(SESSION_KEY));
  }, []);

  useEffect(() => {
    if (!session?.session_id || COMPLETE_STATES.has(session.state) || session.state === "cancelled") return;
    const stream = new EventSource(`${API_BASE}/context-sync/openai/session/${session.session_id}/events`);
    stream.addEventListener("progress", (event) => {
      try { setSession(JSON.parse((event as MessageEvent).data)); } catch { /* polling below provides recovery */ }
    });
    const timer = window.setInterval(() => {
      apiGet<TransferSession>(`/context-sync/openai/session/${session.session_id}`).then(setSession).catch(() => undefined);
    }, 2500);
    return () => { stream.close(); window.clearInterval(timer); };
  }, [session?.session_id, session?.state]);

  useEffect(() => {
    if (!session?.ready_for_use || notified.current) return;
    notified.current = true;
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification("Your ChatGPT context is ready", { body: "Your conversations and projects are available in Muslim LLM." });
    }
  }, [session?.ready_for_use]);

  useEffect(() => {
    if (!session?.session_id || !COMPLETE_STATES.has(session.state)) return;
    apiGet<TransferReportResult>(`/context-sync/openai/session/${session.session_id}/report`)
      .then((result) => setReport(result.report))
      .catch(() => setReport(null));
  }, [session?.session_id, session?.state]);

  async function agreeAndConnect() {
    if (!accepted || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await apiPost<AgreeResult>("/context-sync/openai/agree-and-connect", {
        accepted: true,
        device_id: localDeviceId()
      });
      window.localStorage.setItem(SESSION_KEY, result.session_id);
      const current = await apiGet<TransferSession>(`/context-sync/openai/session/${result.session_id}`);
      setSession(current);
      if (result.next_action === "open_official_export" && result.action_url) {
        window.open(result.action_url, "_blank", "noopener,noreferrer");
      }
    } catch {
      setError("Connection unavailable. Please retry.");
    } finally {
      setBusy(false);
    }
  }

  async function grantFolderAccess() {
    if (!session || busy) return;
    setBusy(true);
    setError("");
    try {
      const next = await apiPost<TransferSession>(`/context-sync/openai/session/${session.session_id}/grant-folder-access`, {});
      setSession(next);
      if (next.next_action === "select_file") fileInput.current?.click();
    } catch {
      setError("Folder access was not completed.");
    } finally {
      setBusy(false);
    }
  }

  async function selectExport(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !session) return;
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch(`${API_BASE}/context-sync/openai/session/${session.session_id}/select-export`, { method: "POST", body });
      if (!response.ok) throw new Error("Export file not recognized");
      setSession(await apiGet<TransferSession>(`/context-sync/openai/session/${session.session_id}`));
    } catch {
      setError("That file was not recognized as a ChatGPT export.");
      setSession(await apiGet<TransferSession>(`/context-sync/openai/session/${session.session_id}`).catch(() => session));
    } finally {
      setBusy(false);
    }
  }

  async function resume() {
    if (!session || busy) return;
    setBusy(true);
    setError("");
    try {
      setSession(await apiPost<TransferSession>(`/context-sync/openai/session/${session.session_id}/resume`, {}));
    } catch {
      setError("Sync could not resume yet.");
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (!session || busy) return;
    setBusy(true);
    try {
      setSession(await apiPost<TransferSession>(`/context-sync/openai/session/${session.session_id}/cancel`, {}));
    } finally {
      setBusy(false);
    }
  }

  function startAgain() {
    window.localStorage.removeItem(SESSION_KEY);
    setSession(null);
    setAccepted(false);
    setError("");
    setReport(null);
  }

  const complete = Boolean(session && COMPLETE_STATES.has(session.state));
  const waitingForExport = session?.state === "awaiting_file_selection" || session?.state === "waiting_for_export" || session?.state === "watching_email" || session?.state === "watching_folder";
  const eta = etaLabel(session?.estimated_seconds_remaining);

  return (
    <main className="geometric-field min-h-dvh bg-background px-4 py-5 text-foreground sm:px-7 sm:py-7">
      <input ref={fileInput} hidden type="file" accept=".zip,application/zip" onChange={selectExport} />
      <div className="relative z-10 mx-auto flex min-h-[calc(100dvh-2.5rem)] max-w-5xl flex-col sm:min-h-[calc(100dvh-3.5rem)]">
        <header className="flex items-center justify-between">
          <Link className="inline-flex h-9 items-center gap-2 rounded-md px-2 text-sm text-muted-foreground transition hover:bg-muted hover:text-foreground" href="/">
            <ArrowLeft size={16} /> Back
          </Link>
          <div className="inline-flex items-center gap-2 text-xs text-muted-foreground"><LockKeyhole size={14} /> Private by default</div>
        </header>

        <section className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center py-12">
          {!session ? (
            <div>
              <div className="text-center">
                <span className="mx-auto grid h-12 w-12 place-items-center rounded-lg bg-primary text-primary-foreground"><Import size={21} /></span>
                <h1 className="display-type mt-6 text-3xl font-semibold leading-tight sm:text-5xl">Bring your ChatGPT context with you</h1>
                <p className="mx-auto mt-4 max-w-lg text-sm leading-6 text-muted-foreground sm:text-base">Transfer your available conversations, projects, files, and working context into Muslim LLM.</p>
              </div>
              <label className="mx-auto mt-8 flex max-w-lg cursor-pointer items-start gap-3 rounded-lg border bg-card/70 p-4 text-sm leading-6">
                <input className="mt-1 h-4 w-4 shrink-0 accent-[hsl(var(--primary))]" type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} />
                <span>I authorize Muslim LLM to process the official ChatGPT data export that I provide for this transfer.</span>
              </label>
              <button className="mx-auto mt-5 flex h-11 items-center justify-center gap-2 rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-45" disabled={!accepted || busy} onClick={agreeAndConnect} type="button">
                {busy ? <LoaderCircle className="animate-spin motion-reduce:animate-none" size={17} /> : null} Connect ChatGPT
              </button>
              <p className="mt-4 text-center text-xs text-muted-foreground">Your imported data remains on this device by default.</p>
            </div>
          ) : complete ? (
            <div className="text-center">
              <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-primary text-primary-foreground"><Check size={22} /></span>
              <h1 className="display-type mt-6 text-3xl font-semibold sm:text-5xl">Your ChatGPT context is ready</h1>
              <p className="mt-3 text-sm text-muted-foreground">Your available context has been restored and validated.</p>
              <div className="mt-8 grid grid-cols-2 divide-x border-y py-4 text-center sm:grid-cols-4">
                <div className="px-2"><strong className="block text-lg">{report?.conversations_imported ?? session.chats_restored}</strong><span className="text-[11px] text-muted-foreground">Chats</span></div>
                <div className="px-2"><strong className="block text-lg">{report?.projects_transferred ?? session.projects_restored}</strong><span className="text-[11px] text-muted-foreground">Projects</span></div>
                <div className="border-t px-2 pt-4 sm:border-t-0 sm:pt-0"><strong className="block text-lg">{report?.files_imported ?? session.files_restored}</strong><span className="text-[11px] text-muted-foreground">Files</span></div>
                <div className="border-t px-2 pt-4 sm:border-t-0 sm:pt-0"><strong className="block text-lg">{durationLabel(report?.sync_duration_seconds ?? session.sync_duration_seconds)}</strong><span className="text-[11px] text-muted-foreground">Duration</span></div>
              </div>
              <p className="mt-4 text-xs font-medium text-primary">{report?.validation_status === "passed_with_exceptions" ? "Ready with exceptions" : "Transfer complete"}</p>
              <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
                {session.latest_chat_id ? <Link className="inline-flex h-11 items-center justify-center rounded-md border bg-card px-5 text-sm font-semibold transition hover:bg-muted" href={`/?chat=${session.latest_chat_id}`}>Open latest conversation</Link> : null}
                <Link className="inline-flex h-11 items-center justify-center rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground transition hover:opacity-90" href="/">Open Muslim LLM</Link>
              </div>
              {report ? (
                <details className="mx-auto mt-7 max-w-lg border-t pt-4 text-left">
                  <summary className="cursor-pointer text-center text-xs font-semibold text-muted-foreground hover:text-foreground">Sync details</summary>
                  <div className="mt-4 space-y-2 text-xs leading-5 text-muted-foreground">
                    <p>{report.duplicates_prevented} duplicates prevented; {report.continuity_validations_passed}/{report.continuity_validations_run} recent chats ready to continue</p>
                    {report.exceptions.length ? report.exceptions.slice(0, 8).map((item, index) => <p key={`${item.source_object_id ?? "exception"}-${index}`}>{item.user_message || item.error_class || "An imported item needs review."}</p>) : <p>No transfer exceptions.</p>}
                  </div>
                </details>
              ) : null}
            </div>
          ) : session.state === "cancelled" ? (
            <div className="text-center">
              <span className="mx-auto grid h-12 w-12 place-items-center rounded-full border"><X size={21} /></span>
              <h1 className="display-type mt-6 text-3xl font-semibold sm:text-5xl">Transfer cancelled</h1>
              <button className="mt-7 inline-flex h-11 items-center justify-center rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground" onClick={startAgain} type="button">Start again</button>
            </div>
          ) : (
            <div>
              <div className="text-center">
                {waitingForExport ? <Import className="mx-auto text-primary" size={28} /> : <LoaderCircle className="mx-auto animate-spin text-primary motion-reduce:animate-none" size={28} />}
                <h1 className="display-type mt-6 text-3xl font-semibold sm:text-5xl">{waitingForExport ? "Waiting for your ChatGPT export" : "Syncing your ChatGPT context"}</h1>
                <p className="mt-3 text-sm text-muted-foreground">{session.display_message}</p>
                {session.ready_for_use && session.background_sync_continues ? <p className="mt-2 text-xs text-primary">You can start using Muslim LLM while older history continues syncing.</p> : null}
              </div>

              <div className="mt-9 h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${Math.max(session.progress_percent > 0 ? 2 : 0, session.progress_percent)}%` }} /></div>
              <div className="mt-3 flex justify-between text-xs text-muted-foreground"><span>{Math.round(session.progress_percent)}%</span><span>{eta ?? "Estimating time remaining"}</span></div>

              <div className="mt-8 grid grid-cols-3 divide-x border-y py-4 text-center">
                <div><strong className="block text-lg">{session.chats_restored}</strong><span className="text-[11px] text-muted-foreground">Chats</span></div>
                <div><strong className="block text-lg">{session.projects_restored}</strong><span className="text-[11px] text-muted-foreground">Projects</span></div>
                <div><strong className="block text-lg">{session.files_restored}</strong><span className="text-[11px] text-muted-foreground">Files</span></div>
              </div>

              <div className="mt-7 flex flex-col items-center gap-3">
                {session.next_action === "grant_folder_access" ? <button className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-50" disabled={busy} onClick={grantFolderAccess} type="button"><FolderSearch size={16} /> Allow Downloads folder</button> : null}
                {session.next_action === "select_file" ? <><button className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-50" disabled={busy} onClick={() => fileInput.current?.click()} type="button"><Import size={16} /> Select ChatGPT export</button><a className="text-xs font-medium text-muted-foreground transition hover:text-foreground" href={OFFICIAL_EXPORT_URL} rel="noreferrer" target="_blank">Open official export</a></> : null}
                {session.next_action === "resume" ? <button className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-50" disabled={busy} onClick={resume} type="button"><RotateCcw size={16} /> Resume sync</button> : null}
                {session.ready_for_use ? <Link className="inline-flex h-11 items-center justify-center rounded-md border bg-card px-5 text-sm font-semibold transition hover:bg-muted" href={session.latest_chat_id ? `/?chat=${session.latest_chat_id}` : "/"}>Open Muslim LLM</Link> : null}
                <button className="h-8 px-3 text-xs font-medium text-muted-foreground transition hover:text-foreground disabled:opacity-50" disabled={busy} onClick={cancel} type="button">Cancel</button>
              </div>
            </div>
          )}
          {error ? <p className="mt-6 text-center text-sm text-red-700 dark:text-red-300">{error}</p> : null}
        </section>
      </div>
    </main>
  );
}

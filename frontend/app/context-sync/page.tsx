"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, Cpu, LockKeyhole, Unplug } from "lucide-react";
import { useRouter } from "next/navigation";
import { API_BASE, apiDelete, apiGet, apiPost } from "@/lib/api";
import { ConnectionResult, ModelConnection, ProviderCapability, SyncJob } from "@/lib/context-sync/types";
import { ProviderSelection } from "@/components/context-sync/ProviderSelection";
import { ConnectConsent } from "@/components/context-sync/ConnectConsent";
import { ModelConnectionDialog } from "@/components/context-sync/ModelConnectionDialog";
import { SyncProgress } from "@/components/context-sync/SyncProgress";
import { SyncComplete } from "@/components/context-sync/SyncComplete";

type Phase = "select" | "sync" | "complete";

const RETURN_ERRORS: Record<string, string> = {
  connection_expired: "Connection expired. Please try again.",
  connection_temporarily_unavailable: "Secure connection is temporarily unavailable.",
};

export default function ContextSyncPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("select");
  const [providers, setProviders] = useState<ProviderCapability[]>([]);
  const [selected, setSelected] = useState<ProviderCapability | null>(null);
  const [consentProvider, setConsentProvider] = useState<ProviderCapability | null>(null);
  const [showModelConnection, setShowModelConnection] = useState(false);
  const [modelConnection, setModelConnection] = useState<ModelConnection | null>(null);
  const [job, setJob] = useState<SyncJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consentError, setConsentError] = useState<string | null>(null);
  const exportInput = useRef<HTMLInputElement>(null);
  const [exportProvider, setExportProvider] = useState<ProviderCapability | null>(null);

  const destination = job?.entry_chat_id ? `/?chat=${job.entry_chat_id}` : "/";

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const returnedJob = params.get("job");
    const returnedProvider = params.get("provider");
    const returnedError = params.get("error");

    apiGet<ProviderCapability[]>("/context-sync/providers").then((items) => {
      setProviders(items);
      if (returnedProvider) setSelected(items.find((item) => item.provider_id === returnedProvider) || null);
    }).catch(() => setError("Connection temporarily unavailable"));
    apiGet<{ connection: ModelConnection | null }>("/context-sync/model-connections/active")
      .then((data) => setModelConnection(data.connection))
      .catch(() => undefined);

    if (returnedJob) {
      apiGet<SyncJob>(`/context-sync/status/${returnedJob}`).then((next) => {
        setJob(next);
        setPhase(next.status === "completed" || next.status === "completed_with_exceptions" ? "complete" : "sync");
      }).catch(() => setError("Sync paused"));
    } else if (returnedError) {
      setError(RETURN_ERRORS[returnedError] || "Connection temporarily unavailable");
      setPhase("sync");
    } else {
      apiGet<{ active_job?: SyncJob | null }>("/context-sync/status").then((data) => {
        if (data.active_job) {
          setJob(data.active_job);
          setPhase("sync");
        }
      }).catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    if (!job?.id || phase === "complete") return;
    const update = (next: SyncJob) => {
      setJob(next);
      if (next.status === "completed" || next.status === "completed_with_exceptions") setPhase("complete");
    };
    const stream = new EventSource(`${API_BASE}/context-sync/events/${job.id}`);
    stream.addEventListener("progress", (event) => {
      try { update(JSON.parse((event as MessageEvent).data)); } catch { /* polling remains available */ }
    });
    const timer = window.setInterval(async () => {
      try { update(await apiGet<SyncJob>(`/context-sync/status/${job.id}`)); } catch { /* durable backend job continues */ }
    }, 1400);
    return () => { stream.close(); window.clearInterval(timer); };
  }, [job?.id, phase]);

  useEffect(() => {
    if (phase !== "complete") return;
    if (typeof Notification !== "undefined" && Notification.permission === "granted") {
      new Notification("Your AI context is ready", { body: "Your conversations and projects are now available in Muslim LLM." });
    }
    const timer = window.setTimeout(() => router.push(destination), 2200);
    return () => window.clearTimeout(timer);
  }, [destination, phase, router]);

  function openConsent(provider: ProviderCapability) {
    setConsentError(null);
    setConsentProvider(provider);
  }

  async function beginAuthentication(provider: ProviderCapability) {
    if (provider.connection_method === "official_export") {
      setExportProvider(provider);
      setConsentError(null);
      exportInput.current?.click();
      return;
    }
    setBusy(true);
    setConsentError(null);
    try {
      const result = await apiPost<ConnectionResult>(`/context-sync/connect/${provider.provider_id}`, {
        return_uri: `${window.location.origin}/context-sync`,
      });
      if (result.next_action === "redirect" && result.authorization_url) {
        window.location.assign(result.authorization_url);
        return;
      }
      if (result.next_action === "sync" && result.job_id) {
        setSelected(provider);
        setConsentProvider(null);
        setJob(await apiGet<SyncJob>(`/context-sync/status/${result.job_id}`));
        setPhase("sync");
        return;
      }
      setConsentError(result.user_message || `Secure sign-in for ${provider.display_name} is not available yet.`);
    } catch {
      setConsentError("Secure connection is temporarily unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function importOfficialExport(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !exportProvider) return;
    setBusy(true);
    setConsentError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch(`${API_BASE}/context-sync/official-export/${exportProvider.provider_id}`, { method: "POST", body: form });
      if (!response.ok) throw new Error(await response.text());
      const result = await response.json() as ConnectionResult;
      if (!result.job_id) throw new Error("Import did not start");
      setSelected(exportProvider);
      setConsentProvider(null);
      setJob(await apiGet<SyncJob>(`/context-sync/status/${result.job_id}`));
      setPhase("sync");
    } catch {
      setConsentError("That export could not be read. Choose the original provider ZIP or JSON file.");
    } finally {
      event.target.value = "";
      setBusy(false);
    }
  }

  function reset() {
    window.history.replaceState({}, "", "/context-sync");
    setPhase("select");
    setSelected(null);
    setConsentProvider(null);
    setJob(null);
    setError(null);
  }

  async function disconnectModel() {
    if (!modelConnection) return;
    await apiDelete(`/context-sync/model-connections/${modelConnection.id}`);
    setModelConnection(null);
  }

  return (
    <main className="geometric-field min-h-dvh overflow-x-hidden px-4 py-5 sm:px-7 sm:py-7">
      <input ref={exportInput} hidden tabIndex={-1} type="file" accept=".zip,.json,.csv,.txt,.md" onChange={importOfficialExport} />
      <div className="relative z-10 mx-auto max-w-6xl">
        <header className="flex items-center justify-between">
          <Link className="inline-flex h-9 items-center gap-2 rounded-md px-2 text-sm text-muted-foreground transition hover:bg-muted hover:text-foreground" href="/">
            <ArrowLeft size={16} /> Back
          </Link>
          <div className="inline-flex items-center gap-2 text-xs text-muted-foreground"><LockKeyhole size={14} /> Private by default</div>
        </header>

        {phase === "select" ? (
          <div className="pb-12 pt-12 sm:pt-16">
            <div className="mx-auto mb-8 max-w-2xl text-center">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Connections</p>
              <h1 className="display-type mt-3 text-4xl font-semibold leading-tight sm:text-6xl">Your model. Muslim LLM.</h1>
              <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-muted-foreground sm:text-base">Connect privately, test instantly, and start asking.</p>
            </div>

            <section className="mx-auto mb-12 flex w-full max-w-5xl flex-col justify-between gap-5 border-y border-border/80 py-6 sm:flex-row sm:items-center" aria-label="Active model connection">
              <div className="flex min-w-0 items-center gap-4">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground"><Cpu size={20} /></span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2"><h2 className="font-semibold">Muslim LLM</h2>{modelConnection ? <span className="inline-flex items-center gap-1 text-xs font-medium text-primary"><CheckCircle2 size={13} /> Ready</span> : null}</div>
                  <p className="mt-1 truncate text-sm text-muted-foreground">{modelConnection ? (modelConnection.mode === "local" ? "Running on this device" : "Secure API connected") : "Choose a private model connection"}</p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {modelConnection ? <button aria-label="Disconnect model" className="grid h-10 w-10 place-items-center rounded-md border bg-background text-muted-foreground transition hover:border-red-300 hover:text-red-700" onClick={disconnectModel} title="Disconnect" type="button"><Unplug size={17} /></button> : null}
                <button className="h-10 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:opacity-90" onClick={() => setShowModelConnection(true)} type="button">{modelConnection ? "Change" : "Connect model"}</button>
              </div>
            </section>

            <div className="mx-auto mb-5 max-w-5xl">
              <h2 className="text-sm font-semibold">Bring existing chats</h2>
              <p className="mt-1 text-xs text-muted-foreground">Verified provider connections only.</p>
            </div>
            <ProviderSelection providers={providers} onConnect={openConsent} />
          </div>
        ) : phase === "complete" ? (
          <SyncComplete href={destination} />
        ) : (
          <SyncProgress provider={selected} job={job} busy={busy} error={error} onRetry={selected ? () => openConsent(selected) : reset} />
        )}

        {consentProvider ? (
          <ConnectConsent
            provider={consentProvider}
            busy={busy}
            error={consentError}
            onContinue={() => beginAuthentication(consentProvider)}
            onClose={() => { setConsentProvider(null); setConsentError(null); }}
          />
        ) : null}
        {showModelConnection ? (
          <ModelConnectionDialog
            onClose={() => setShowModelConnection(false)}
            onConnected={(connection) => { setModelConnection(connection); setShowModelConnection(false); }}
          />
        ) : null}
      </div>
    </main>
  );
}

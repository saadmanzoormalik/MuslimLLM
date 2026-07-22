"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, FileUp, Import, KeyRound, Lock, RotateCcw, ShieldCheck, Sparkles, Upload } from "lucide-react";
import { API_BASE, apiGet, apiPost } from "@/lib/api";
import { Button, Panel, PrimaryButton, Textarea } from "@/components/ui";

type Provider = {
  provider: string;
  display_name: string;
  supports_api_import: boolean;
  supports_file_import: boolean;
  supports_project_import: boolean;
  supports_attachment_import: boolean;
  supports_memory_import: boolean;
  supports_chat_history_import: boolean;
  preferred_import_mode: string;
  supported_data_types: string[];
  privacy_note: string;
  api_status: { supported: boolean; reason?: string; url?: string };
};

type Preview = {
  job: { id: string; provider: string; status: string; coverage_score?: number; total_items_detected?: number };
  coverage: { overall: number; dimensions?: Record<string, number>; detected?: Record<string, number>; note?: string };
  conversations?: { id: string; title: string; message_count: number; attachment_count: number; token_estimate: number }[];
  projects?: { id: string; title: string; description?: string }[];
  security_warnings?: string[];
  preview_url?: string;
};

type MemorySuggestion = { id: string; content: string; source_provider: string; confidence_level: string; review_status: string };

const timelineOptions = [
  ["last_30_days", "30 days"],
  ["last_90_days", "90 days"],
  ["last_6_months", "6 months"],
  ["last_12_months", "12 months"],
  ["all_time", "All time"],
];

export default function ImportContextPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState("chatgpt");
  const [method, setMethod] = useState<"file" | "paste" | "api">("file");
  const [datePreset, setDatePreset] = useState("last_6_months");
  const [paste, setPaste] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [memories, setMemories] = useState<MemorySuggestion[]>([]);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const provider = useMemo(() => providers.find((item) => item.provider === selectedProvider), [providers, selectedProvider]);

  useEffect(() => {
    apiGet<Provider[]>("/imports/providers").then((items) => {
      setProviders(items);
      if (items[0]) setSelectedProvider(items[0].provider);
    }).catch(() => setProviders([]));
    loadMemories();
  }, []);

  function loadMemories() {
    apiGet<MemorySuggestion[]>("/imports/memory-suggestions").then(setMemories).catch(() => setMemories([]));
  }

  async function scanFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    if (!(file instanceof File) || file.size === 0) {
      setStatus("Choose an export file first.");
      return;
    }
    form.set("date_preset", datePreset);
    setBusy(true);
    setStatus("Scanning locally...");
    try {
      const response = await fetch(`${API_BASE}/imports/upload/${selectedProvider}`, { method: "POST", body: form });
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      setPreview(data);
      setStatus("Preview ready.");
    } catch (error) {
      setStatus(String(error));
    } finally {
      setBusy(false);
    }
  }

  async function scanPaste() {
    if (!paste.trim()) {
      setStatus("Paste a transcript or project note first.");
      return;
    }
    setBusy(true);
    setStatus("Scanning pasted context...");
    try {
      const data = await apiPost<Preview>("/imports/paste", {
        provider: selectedProvider,
        title: "Pasted import",
        content: paste,
        date_range: { preset: datePreset },
        options: {}
      });
      setPreview(data);
      setStatus("Preview ready.");
    } catch (error) {
      setStatus(String(error));
    } finally {
      setBusy(false);
    }
  }

  async function connectProvider() {
    setBusy(true);
    try {
      const result = await apiPost<{ supported: boolean; reason?: string; url?: string }>(`/imports/connect/${selectedProvider}`, { date_range: { preset: datePreset } });
      setStatus(result.supported ? "Connection ready." : result.reason || "Upload export required.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmImport() {
    if (!preview?.job?.id) return;
    setBusy(true);
    setStatus("Importing locally...");
    try {
      const result = await apiPost<{ imported: number; skipped: number; status: string }>(`/imports/jobs/${preview.job.id}/confirm`, {
        options: {
          import_chats: true,
          import_projects: true,
          import_files: false,
          generate_summaries: true,
          generate_memory_suggestions: true,
          rebuild_context_graph: true,
          add_files_to_rag: false,
          keep_provider_names_visible: true,
          cloud_summarization_enabled: false
        }
      });
      setStatus(`Imported ${result.imported}. Skipped ${result.skipped}.`);
      const detail = await apiGet<Preview>(`/imports/jobs/${preview.job.id}/preview`);
      setPreview(detail);
      loadMemories();
    } catch (error) {
      setStatus(String(error));
    } finally {
      setBusy(false);
    }
  }

  async function reviewMemory(id: string, decision: "accept" | "reject") {
    await apiPost(`/imports/memory-suggestions/${id}/${decision}`, {});
    loadMemories();
  }

  return (
    <main className="civilizational-surface min-h-dvh px-4 py-6">
      <div className="mx-auto max-w-6xl">
        <Link className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground" href="/settings"><ArrowLeft size={16} /> Settings</Link>
        <div className="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
          <section>
            <div className="inline-flex items-center gap-2 rounded-full border bg-card/80 px-3 py-1 text-xs font-medium text-muted-foreground">
              <Import size={14} /> Bring your AI context with you
            </div>
            <h1 className="display-type mt-3 text-4xl font-semibold leading-none sm:text-6xl">Import Context</h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
              Import chats, projects, files, and preferences from other assistants. Local by default.
            </p>
            <div className="mt-5 grid gap-3">
              <Step icon={<ShieldCheck size={16} />} title="Local first" text="No imported data leaves this machine unless cloud mode is explicitly built and enabled." />
              <Step icon={<Lock size={16} />} title="Transparent coverage" text="Unavailable provider fields are shown instead of guessed." />
              <Step icon={<Sparkles size={16} />} title="Review memories" text="Memory suggestions wait for approval." />
            </div>
          </section>

          <Panel className="glass-panel p-4">
            <div className="grid gap-4">
              <section>
                <h2 className="text-sm font-semibold">1. Source</h2>
                <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                  {providers.map((item) => (
                    <button
                      key={item.provider}
                      className={`rounded-lg border p-3 text-left transition hover:border-primary/45 ${selectedProvider === item.provider ? "border-primary bg-primary/8" : "bg-card/70"}`}
                      onClick={() => setSelectedProvider(item.provider)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold">{item.display_name}</span>
                        {item.supports_api_import ? <KeyRound size={14} /> : <FileUp size={14} />}
                      </div>
                      <p className="mt-2 text-xs leading-5 text-muted-foreground">{item.supports_api_import ? "One-click available" : "Upload export required"}</p>
                    </button>
                  ))}
                </div>
              </section>

              <section className="grid gap-3 md:grid-cols-[1fr_1fr]">
                <div>
                  <h2 className="text-sm font-semibold">2. Method</h2>
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {(["file", "paste", "api"] as const).map((item) => (
                      <button key={item} className={`rounded-lg border px-3 py-2 text-sm capitalize ${method === item ? "border-primary bg-primary/10" : "bg-card/70"}`} onClick={() => setMethod(item)}>
                        {item === "api" ? "Connect" : item}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <h2 className="text-sm font-semibold">3. Timeline</h2>
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {timelineOptions.map(([value, label]) => (
                      <button key={value} className={`rounded-lg border px-3 py-2 text-sm ${datePreset === value ? "border-primary bg-primary/10" : "bg-card/70"}`} onClick={() => setDatePreset(value)}>
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </section>

              {provider ? (
                <div className="rounded-lg border bg-background/55 p-3 text-xs leading-5 text-muted-foreground">
                  {provider.api_status.reason || provider.privacy_note} Supports: {provider.supported_data_types.join(", ")}.
                </div>
              ) : null}

              {method === "file" ? (
                <form className="rounded-lg border bg-card/70 p-3" onSubmit={scanFile}>
                  <input type="hidden" name="date_preset" value={datePreset} />
                  <input className="w-full rounded-md border bg-background p-2 text-sm" name="file" type="file" accept=".json,.jsonl,.zip,.md,.txt,.csv" />
                  <PrimaryButton className="mt-3 w-full" type="submit" disabled={busy}><Upload size={16} /> Scan upload</PrimaryButton>
                </form>
              ) : null}

              {method === "paste" ? (
                <div className="rounded-lg border bg-card/70 p-3">
                  <Textarea className="min-h-36 w-full" value={paste} onChange={(event) => setPaste(event.target.value)} placeholder="Paste transcript, project summary, or exported notes..." />
                  <PrimaryButton className="mt-3 w-full" onClick={scanPaste} disabled={busy}><Sparkles size={16} /> Scan paste</PrimaryButton>
                </div>
              ) : null}

              {method === "api" ? (
                <div className="rounded-lg border bg-card/70 p-3">
                  <p className="text-sm text-muted-foreground">If the provider does not expose full chat export APIs, Muslim LLM will show the upload fallback clearly.</p>
                  <PrimaryButton className="mt-3 w-full" onClick={connectProvider} disabled={busy}><KeyRound size={16} /> Check connection</PrimaryButton>
                </div>
              ) : null}
            </div>
          </Panel>
        </div>

        {preview ? (
          <section className="mt-5 grid gap-4 lg:grid-cols-[0.75fr_1.25fr]">
            <Panel className="glass-panel p-4">
              <h2 className="text-sm font-semibold">Preview</h2>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <Stat label="Coverage" value={`${Number(preview.coverage?.overall ?? preview.job.coverage_score ?? 0).toFixed(1)}%`} />
                <Stat label="Chats" value={String(preview.conversations?.length ?? preview.coverage?.detected?.chats ?? preview.job.total_items_detected ?? 0)} />
                <Stat label="Projects" value={String(preview.projects?.length ?? preview.coverage?.detected?.projects ?? 0)} />
                <Stat label="Warnings" value={String(preview.security_warnings?.length ?? 0)} />
              </div>
              <PrimaryButton className="mt-4 w-full" onClick={confirmImport} disabled={busy || preview.job.status === "completed"}><CheckCircle2 size={16} /> Confirm import</PrimaryButton>
              <div className="mt-3 flex gap-2">
                <a className="inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-md border bg-card px-3 text-sm" href={`${API_BASE}/imports/jobs/${preview.job.id}/report?format=markdown`} target="_blank">Report</a>
                <a className="inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-md border bg-card px-3 text-sm" href={`${API_BASE}/imports/jobs/${preview.job.id}/report?format=csv`} target="_blank">CSV</a>
              </div>
            </Panel>

            <Panel className="glass-panel overflow-hidden">
              <div className="border-b p-4">
                <h2 className="text-sm font-semibold">Detected chats</h2>
              </div>
              <div className="max-h-[420px] overflow-auto">
                {(preview.conversations || []).length === 0 ? (
                  <p className="p-4 text-sm text-muted-foreground">No chats detected in this range.</p>
                ) : (preview.conversations || []).slice(0, 30).map((chat) => (
                  <div key={chat.id} className="border-b p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-semibold">{chat.title}</p>
                      <span className="text-xs text-muted-foreground">{chat.message_count} messages</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{chat.token_estimate} estimated tokens · {chat.attachment_count} attachments</p>
                  </div>
                ))}
              </div>
            </Panel>
          </section>
        ) : null}

        <section className="mt-5 grid gap-4 lg:grid-cols-2">
          <Panel className="glass-panel p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Memory review</h2>
              <Button className="h-8" onClick={loadMemories}><RotateCcw size={14} /> Refresh</Button>
            </div>
            <div className="mt-3 grid gap-2">
              {memories.length === 0 ? <p className="text-sm text-muted-foreground">No pending suggestions.</p> : memories.slice(0, 8).map((memory) => (
                <div key={memory.id} className="rounded-lg border bg-background/55 p-3">
                  <p className="text-sm leading-6">{memory.content}</p>
                  <div className="mt-2 flex gap-2">
                    <Button className="h-8" onClick={() => reviewMemory(memory.id, "accept")}>Accept</Button>
                    <Button className="h-8" onClick={() => reviewMemory(memory.id, "reject")}>Reject</Button>
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel className="glass-panel p-4">
            <h2 className="text-sm font-semibold">Status</h2>
            <p className="mt-3 rounded-lg border bg-background/55 p-3 text-sm leading-6 text-muted-foreground">{status || "Choose a source to begin."}</p>
            <p className="mt-3 text-xs leading-5 text-muted-foreground">Imported chats appear under All Chats. Imported projects appear under Projects, while chats remain visually distinct in All Chats.</p>
          </Panel>
        </section>
      </div>
    </main>
  );
}

function Step({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-lg border bg-card/70 p-3">
      <div className="flex items-center gap-2 text-sm font-semibold">{icon}{title}</div>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{text}</p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-background/55 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

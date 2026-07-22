"use client";

import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle, ArrowLeft, Check, ChevronRight, CircleStop, CloudCog, FileArchive,
  FlaskConical, History, KeyRound, LoaderCircle, MessageSquare, Play, RotateCcw,
  ShieldCheck, Sparkles, Upload, X
} from "lucide-react";
import { API_BASE, apiGet, apiPost } from "@/lib/api";

type Job = {
  id: string; provider: string; status: string; stage: string; progress: number;
  source_filename?: string; inventory_json?: Record<string, number>; counts_json?: Record<string, number>;
  estimated_seconds_remaining?: number; last_error?: string;
};
type Preview = {
  conversations: Array<Record<string, any>>; projects: Array<Record<string, any>>;
  files: Array<Record<string, any>>; continuity_packages: Array<Record<string, any>>;
  exceptions: Array<Record<string, any>>;
};
type Validation = { status: string; score: number; report_json: { metrics?: Record<string, number>; gates?: Record<string, boolean> } };

const EMPTY_PREVIEW: Preview = { conversations: [], projects: [], files: [], continuity_packages: [], exceptions: [] };
const PROVIDERS = ["OpenAI / ChatGPT", "Claude", "Gemini", "Demo Provider"];

function label(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function ContextSyncLabPage() {
  const picker = useRef<HTMLInputElement>(null);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [provider, setProvider] = useState("OpenAI / ChatGPT");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [preview, setPreview] = useState<Preview>(EMPTY_PREVIEW);
  const [validation, setValidation] = useState<Validation>({ status: "Not tested", score: 0, report_json: {} });
  const [tab, setTab] = useState<"chats" | "projects" | "files" | "continuity">("chats");
  const [selectedChat, setSelectedChat] = useState<string>("");
  const [question, setQuestion] = useState("What should we continue with next?");
  const [continuation, setContinuation] = useState("");
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [apiDialog, setApiDialog] = useState(false);
  const [apiResult, setApiResult] = useState<Record<string, any> | null>(null);

  async function refreshJobs(preferId?: string) {
    try {
      const next = await apiGet<Job[]>("/context-sync-lab/jobs");
      setJobs(next);
      const active = next.find((item) => item.id === (preferId || job?.id)) || next[0] || null;
      setJob(active);
      if (active && ["completed", "completed_with_exceptions"].includes(active.status)) {
        const [nextPreview, nextValidation] = await Promise.all([
          apiGet<Preview>(`/context-sync-lab/jobs/${active.id}/preview`),
          apiGet<Validation>(`/context-sync-lab/jobs/${active.id}/validation`)
        ]);
        setPreview(nextPreview);
        setValidation(nextValidation);
        setSelectedChat((current) => current || nextPreview.conversations[0]?.source_conversation_id || "");
      }
    } catch {
      setAvailable(false);
    }
  }

  useEffect(() => {
    apiGet("/context-sync-lab/providers").then(() => { setAvailable(true); refreshJobs(); }).catch(() => setAvailable(false));
  }, []);

  useEffect(() => {
    if (!job || ["completed", "completed_with_exceptions", "failed", "cancelled"].includes(job.status)) return;
    const timer = window.setInterval(() => refreshJobs(job.id), 1200);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.status]);

  async function openExport() {
    setBusy("export");
    try {
      const result = await apiPost<{ url: string }>("/context-sync-lab/openai/request-export", {});
      window.open(result.url, "_blank", "noopener,noreferrer");
      setNotice("Waiting for export");
    } finally { setBusy(""); }
  }

  async function selectExport(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy("upload"); setNotice("Inspecting export locally");
    try {
      const form = new FormData(); form.append("file", file);
      const response = await fetch(`${API_BASE}/context-sync-lab/openai/select-export`, { method: "POST", body: form });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "Import could not start");
      const result = await response.json();
      setNotice(result.duplicate_export ? "Existing import opened" : "Import started");
      await refreshJobs(result.job_id);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Import could not start");
    } finally {
      event.target.value = ""; setBusy("");
    }
  }

  async function retry() {
    if (!job) return; setBusy("retry");
    try { await apiPost(`/context-sync-lab/jobs/${job.id}/retry`, {}); await refreshJobs(job.id); }
    finally { setBusy(""); }
  }

  async function cancel() {
    if (!job) return; await apiPost(`/context-sync-lab/jobs/${job.id}/cancel`, {}); await refreshJobs(job.id);
  }

  async function testContinuation() {
    if (!job || !selectedChat || !question.trim()) return;
    setBusy("continuation"); setContinuation("");
    try {
      const result = await apiPost<{ answer: string; source_refs: string[] }>(`/context-sync-lab/jobs/${job.id}/test-continuation`, { source_conversation_id: selectedChat, question });
      setContinuation(result.answer);
    } catch { setContinuation("The sandbox could not reach the local model. Your imported data was not changed."); }
    finally { setBusy(""); }
  }

  async function promote() {
    if (!job) return; setBusy("promote");
    try {
      const result = await apiPost<Record<string, number>>(`/context-sync-lab/jobs/${job.id}/promote`, { include_suggested_projects: false });
      setNotice(`${result.promoted_chats || 0} chats promoted`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Promotion did not run"); }
    finally { setBusy(""); }
  }

  const inventory = job?.inventory_json || job?.counts_json || {};
  const activeRows = useMemo(() => tab === "chats" ? preview.conversations : tab === "projects" ? preview.projects : tab === "files" ? preview.files : preview.continuity_packages, [preview, tab]);
  const canPromote = ["Release candidate", "Passed with exceptions"].includes(validation.status);

  if (available === false) {
    return <main className="min-h-dvh bg-[#101a17] px-5 py-16 text-[#f5f0e4]"><div className="mx-auto max-w-xl"><span className="text-xs font-semibold uppercase text-[#d6b65f]">Development Lab</span><h1 className="display-type mt-4 text-4xl">Context Sync Lab is off.</h1><p className="mt-3 text-sm text-[#aab8b2]">Start the isolated environment with <code>./deployment/context-sync-macos/start-lab.sh</code>.</p><Link className="mt-7 inline-flex items-center gap-2 text-sm" href="/"><ArrowLeft size={16}/> Return to Muslim LLM</Link></div></main>;
  }

  return (
    <main className="min-h-dvh bg-[#f4f1e8] text-[#12251f] dark:bg-[#0d1714] dark:text-[#f2eee2]">
      <input ref={picker} hidden type="file" accept=".zip,application/zip" onChange={selectExport}/>
      <header className="border-b border-[#c9c3b4] bg-[#132a23] text-[#f6f0df] dark:border-[#33453f]">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-7">
          <div className="flex min-w-0 items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-md border border-[#bfa75f]/50 bg-[#f6f0df]/5"><FlaskConical size={18}/></span><div><div className="flex items-center gap-2"><h1 className="font-semibold">Context Sync Lab</h1><span className="rounded-full border border-[#d6b65f]/60 px-2 py-0.5 text-[10px] font-semibold uppercase text-[#e3c873]">Development Lab</span></div><p className="text-xs text-[#afbeb7]">Isolated from Muslim LLM</p></div></div>
          <Link className="inline-flex h-9 items-center gap-2 rounded-md px-3 text-sm hover:bg-white/10" href="/"><ArrowLeft size={15}/> Return</Link>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-7 sm:px-7">
        <section className="border-b border-[#c9c3b4] pb-7 dark:border-[#33453f]">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase text-[#8a6d26] dark:text-[#d6b65f]">Provider</p><h2 className="mt-1 text-xl font-semibold">Connect your ChatGPT context</h2></div><div className="flex gap-2"><button className="inline-flex h-9 items-center gap-2 rounded-md border border-[#aaa493] px-3 text-sm hover:bg-black/5 dark:border-[#475a53] dark:hover:bg-white/5" onClick={() => setApiDialog(true)}><KeyRound size={15}/> OpenAI API Test</button></div></div>
          <div className="grid gap-px overflow-hidden rounded-md border border-[#aaa493] bg-[#aaa493] sm:grid-cols-4 dark:border-[#475a53] dark:bg-[#475a53]">
            {PROVIDERS.map((name) => <button key={name} className={`min-h-14 bg-[#faf8f2] px-3 text-left text-sm transition dark:bg-[#13201c] ${provider === name ? "font-semibold text-[#176348] shadow-[inset_0_-3px_0_#b39135] dark:text-[#72c5a5]" : "text-[#657069] hover:bg-white dark:hover:bg-[#182a24]"}`} onClick={() => setProvider(name)}><span className="flex items-center justify-between">{name}{name === "OpenAI / ChatGPT" ? <Check size={14}/> : <span className="text-[10px] uppercase">Soon</span>}</span></button>)}
          </div>
          {provider === "OpenAI / ChatGPT" ? <div className="mt-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div className="max-w-2xl"><p className="text-sm">Import your official ChatGPT export into this private workspace.</p><p className="mt-1 text-xs text-[#66736d] dark:text-[#9baba4]">ChatGPT will provide a secure export download when it is ready.</p></div><div className="flex flex-wrap gap-2"><button className="inline-flex h-10 items-center gap-2 rounded-md border border-[#aaa493] px-4 text-sm font-medium hover:bg-white dark:border-[#475a53] dark:hover:bg-white/5" onClick={openExport} disabled={!!busy}><CloudCog size={16}/> Open export settings</button><button className="inline-flex h-10 items-center gap-2 rounded-md bg-[#176348] px-4 text-sm font-semibold text-white hover:bg-[#12523b] disabled:opacity-50" onClick={() => picker.current?.click()} disabled={!!busy}>{busy === "upload" ? <LoaderCircle className="animate-spin" size={16}/> : <Upload size={16}/>} Select export ZIP</button></div></div> : <p className="mt-5 text-sm text-[#66736d]">Connector reserved. No account access is attempted.</p>}
          {notice ? <button className="mt-4 inline-flex items-center gap-2 text-xs text-[#6c5a2e] dark:text-[#d6c38c]" onClick={() => setNotice("")}><Sparkles size={13}/>{notice}<X size={12}/></button> : null}
        </section>

        <section className="grid border-b border-[#c9c3b4] py-7 dark:border-[#33453f] lg:grid-cols-[1.1fr_1.9fr] lg:gap-10">
          <div className="lg:border-r lg:border-[#c9c3b4] lg:pr-10 dark:lg:border-[#33453f]">
            <div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase text-[#8a6d26] dark:text-[#d6b65f]">Sync state</p><h2 className="mt-1 text-lg font-semibold">{job ? label(job.stage) : "No import yet"}</h2></div>{job?.status === "failed" ? <button className="grid h-9 w-9 place-items-center rounded-md border" title="Retry" onClick={retry}><RotateCcw size={15}/></button> : job && !job.status.startsWith("completed") ? <button className="grid h-9 w-9 place-items-center rounded-md border" title="Cancel" onClick={cancel}><CircleStop size={15}/></button> : null}</div>
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-[#d8d3c6] dark:bg-[#293b35]"><div className="h-full bg-[#b39135] transition-all" style={{width: `${Number(job?.progress || 0)}%`}}/></div>
            <div className="mt-5 grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
              {[['Conversations', inventory.conversations_found], ['Messages', inventory.messages_found], ['Files', inventory.files_found], ['Branches', inventory.branches_found], ['Projects', preview.projects.length], ['Exceptions', inventory.exceptions]].map(([name, value]) => <div key={String(name)} className="border-b border-[#d6d0c2] pb-2 dark:border-[#293b35]"><span className="block text-xs text-[#66736d] dark:text-[#9baba4]">{name}</span><strong className="mt-1 block text-lg font-semibold">{Number(value || 0).toLocaleString()}</strong></div>)}
            </div>
            {job?.last_error ? <p className="mt-4 flex gap-2 text-xs text-red-700 dark:text-red-300"><AlertTriangle className="shrink-0" size={14}/>{job.last_error}</p> : null}
            {jobs.length > 1 ? <select aria-label="Import history" className="mt-5 h-9 w-full rounded-md border bg-transparent px-2 text-xs" value={job?.id || ""} onChange={(event) => refreshJobs(event.target.value)}>{jobs.map((item) => <option key={item.id} value={item.id}>{item.source_filename || "OpenAI export"} · {label(item.status)}</option>)}</select> : null}
          </div>

          <div className="mt-8 min-w-0 lg:mt-0">
            <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase text-[#8a6d26] dark:text-[#d6b65f]">Preview</p><h2 className="mt-1 text-lg font-semibold">Imported workspace</h2></div><div className="flex border-b border-[#bbb5a7] text-xs dark:border-[#475a53]">{(["chats", "projects", "files", "continuity"] as const).map((item) => <button key={item} className={`px-3 py-2 capitalize ${tab === item ? "border-b-2 border-[#176348] font-semibold" : "text-[#66736d]"}`} onClick={() => setTab(item)}>{item}</button>)}</div></div>
            <div className="mt-4 max-h-[340px] overflow-auto border-y border-[#c9c3b4] dark:border-[#33453f]">
              {activeRows.length ? activeRows.map((item, index) => {
                const sourceId = item.source_conversation_id || item.source_project_id || item.source_path || `${tab}-${index}`;
                return <button key={sourceId} className={`flex w-full items-center justify-between gap-3 border-b border-[#ded9cd] px-1 py-3 text-left last:border-0 dark:border-[#293b35] ${tab === "chats" && selectedChat === item.source_conversation_id ? "text-[#176348] dark:text-[#72c5a5]" : ""}`} onClick={() => item.source_conversation_id && setSelectedChat(item.source_conversation_id)}><span className="min-w-0"><strong className="block truncate text-sm font-medium">{item.title || item.filename || item.source_conversation_id}</strong><span className="mt-1 block truncate text-xs text-[#718078] dark:text-[#90a199]">{tab === "chats" ? `${item.message_count} messages · ${item.branch_count} alternate branches` : tab === "projects" ? label(item.status) : tab === "files" ? `${item.scan_status} · ${Number(item.size_bytes || 0).toLocaleString()} bytes` : `${Math.round(Number(item.confidence || 0) * 100)}% continuity confidence`}</span></span><ChevronRight className="shrink-0" size={14}/></button>;
              }) : <div className="py-12 text-center text-sm text-[#718078]">Import an export to inspect {tab}.</div>}
            </div>
          </div>
        </section>

        <section className="grid gap-10 py-7 lg:grid-cols-2">
          <div>
            <div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase text-[#8a6d26] dark:text-[#d6b65f]">Validation</p><h2 className="mt-1 text-lg font-semibold">{validation.status}</h2></div><div className="text-right"><strong className="text-3xl font-semibold">{Math.round(Number(validation.score || 0))}</strong><span className="text-xs text-[#718078]"> / 100</span></div></div>
            <div className="mt-5 grid gap-2 text-xs">{Object.entries(validation.report_json?.metrics || {}).map(([name, score]) => <div key={name} className="grid grid-cols-[1fr_100px_32px] items-center gap-3"><span>{label(name)}</span><span className="h-1 rounded-full bg-[#d8d3c6] dark:bg-[#293b35]"><span className="block h-full rounded-full bg-[#176348]" style={{width: `${score}%`}}/></span><strong>{Math.round(score)}</strong></div>)}</div>
            <button className="mt-6 inline-flex h-10 items-center gap-2 rounded-md bg-[#132a23] px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40" disabled={!job || !canPromote || !!busy} onClick={promote}><ShieldCheck size={16}/>{busy === "promote" ? "Promoting" : "Promote to Muslim LLM"}</button>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-[#8a6d26] dark:text-[#d6b65f]">Continuation sandbox</p><h2 className="mt-1 text-lg font-semibold">Test imported context</h2>
            <select aria-label="Conversation for continuation test" className="mt-4 h-10 w-full rounded-md border bg-transparent px-3 text-sm" value={selectedChat} onChange={(event) => setSelectedChat(event.target.value)}><option value="">Select a chat</option>{preview.conversations.map((item) => <option key={item.source_conversation_id} value={item.source_conversation_id}>{item.title}</option>)}</select>
            <div className="mt-2 flex gap-2"><input className="h-10 min-w-0 flex-1 rounded-md border bg-transparent px-3 text-sm outline-none focus:ring-2 focus:ring-[#176348]" value={question} onChange={(event) => setQuestion(event.target.value)}/><button aria-label="Test continuation" title="Test continuation" className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-[#176348] text-white disabled:opacity-40" disabled={!selectedChat || busy === "continuation"} onClick={testContinuation}>{busy === "continuation" ? <LoaderCircle className="animate-spin" size={16}/> : <Play size={16}/>}</button></div>
            {continuation ? <div className="mt-4 border-l-2 border-[#b39135] pl-4 text-sm leading-6"><div className="mb-2 flex items-center gap-2 text-xs font-semibold text-[#66736d]"><MessageSquare size={13}/> Sandboxed response</div>{continuation}</div> : <p className="mt-3 text-xs text-[#718078]">Uses local continuity context. Production chat history stays unchanged.</p>}
          </div>
        </section>
      </div>

      {apiDialog ? <div className="fixed inset-0 z-50 grid place-items-center bg-black/55 p-4" role="dialog" aria-modal="true"><form className="w-full max-w-md rounded-md border border-[#4a5e56] bg-[#f8f5ec] p-5 shadow-2xl dark:bg-[#12201b]" onSubmit={async (event) => {event.preventDefault(); setBusy("api"); const form = new FormData(event.currentTarget); try {setApiResult(await apiPost("/context-sync-lab/openai-api/test", {api_base: form.get("api_base"), model: form.get("model"), api_key: form.get("api_key")}));} catch {setApiResult({status:"failed", key_stored:false});} finally {setBusy("");}}}><div className="flex items-center justify-between"><div><h2 className="font-semibold">OpenAI API Test</h2><p className="mt-1 text-xs text-[#718078]">API access is separate from ChatGPT history.</p></div><button aria-label="Close" type="button" onClick={() => setApiDialog(false)}><X size={18}/></button></div><label className="mt-5 grid gap-1 text-xs">API base<input name="api_base" className="h-10 rounded-md border bg-transparent px-3 text-sm" defaultValue="https://api.openai.com/v1"/></label><label className="mt-3 grid gap-1 text-xs">Model<input name="model" className="h-10 rounded-md border bg-transparent px-3 text-sm" defaultValue="gpt-4.1-mini"/></label><label className="mt-3 grid gap-1 text-xs">Temporary API key<input name="api_key" type="password" autoComplete="off" className="h-10 rounded-md border bg-transparent px-3 text-sm" placeholder="Not stored"/></label><button className="mt-5 h-10 w-full rounded-md bg-[#176348] text-sm font-semibold text-white" disabled={busy === "api"}>{busy === "api" ? "Testing" : "Run test"}</button>{apiResult ? <p className="mt-3 flex items-center gap-2 text-xs"><History size={13}/>{label(String(apiResult.status))} · Key not stored</p> : null}</form></div> : null}
    </main>
  );
}

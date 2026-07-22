"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { Activity, ArrowLeft, FlaskConical, Import, LogOut, RefreshCcw, Save, ShieldCheck, Trash2, UserRound } from "lucide-react";
import { API_BASE, apiGet, apiPost } from "@/lib/api";
import { Input, Panel, PrimaryButton } from "@/components/ui";
import { useAuth } from "@/components/auth/AuthBoundary";

export default function SettingsPage() {
  const { user } = useAuth();
  const contextSyncLabEnabled = process.env.NEXT_PUBLIC_ENABLE_CONTEXT_SYNC_LAB === "true";
  const [settings, setSettings] = useState<Record<string, any>>({});
  const [status, setStatus] = useState("");
  const [diagnostics, setDiagnostics] = useState<Record<string, any> | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    apiGet<Record<string, any>>("/settings").then(setSettings).catch(() => setSettings({}));
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await apiPost("/settings", {
      key: "llm",
      value: {
        model: form.get("model"),
        temperature: Number(form.get("temperature") || 0.3)
      }
    });
    await apiPost("/settings", {
      key: "retrieval",
      value: {
        top_k: Number(form.get("top_k") || 6),
        islamic_threshold: Number(form.get("islamic_threshold") || 0.35)
      }
    });
    setStatus("Settings saved.");
  }

  async function runDiagnostics() {
    setChecking(true);
    try {
      setDiagnostics(await apiGet<Record<string, any>>("/chat/diagnostics"));
    } finally {
      setChecking(false);
    }
  }

  async function signOut(all = false) {
    await fetch(`${API_BASE}/auth/${all ? "logout-all" : "logout"}`, { method: "POST", credentials: "include" });
    window.location.replace("/auth");
  }

  async function deleteAccount() {
    if (!window.confirm("Delete this account and its chats? This cannot be undone.")) return;
    const response = await fetch(`${API_BASE}/account`, { method: "DELETE", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirmation: "DELETE" }) });
    if (response.ok) window.location.replace("/onboarding");
    else setStatus((await response.json()).detail || "Account deletion could not be completed.");
  }

  return (
    <main className="min-h-dvh px-4 py-6">
      <div className="mx-auto max-w-3xl">
        <Link className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground" href="/"><ArrowLeft size={16} /> Back to chat</Link>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="mt-2 text-muted-foreground">Control the model and retrieval behavior for the MVP.</p>
        <Panel className="mt-6 overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b p-4">
            <div className="flex min-w-0 items-center gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">{user?.account_type === "guest" ? <UserRound size={18} /> : <ShieldCheck size={18} />}</span><span className="min-w-0"><span className="block text-sm font-semibold">{user?.account_type === "guest" ? "Guest workspace" : user?.display_name || user?.email || "Account"}</span><span className="block truncate text-xs text-muted-foreground">{user?.account_type === "guest" ? "Stored on this device" : user?.email}</span></span></div>
            <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary">{user?.account_type === "guest" ? "Guest" : "Verified"}</span>
          </div>
          {user?.account_type === "user" ? <div className="grid gap-2 border-b p-4 text-sm">{["apple", "google", "email"].map((provider) => { const connected = user.identities?.some((identity) => identity.provider === provider); return <div className="flex items-center justify-between" key={provider}><span className="capitalize">{provider}</span><span className={connected ? "text-primary" : "text-muted-foreground"}>{connected ? "Connected" : "Not connected"}</span></div>; })}</div> : <div className="border-b p-4 text-sm text-muted-foreground">Connect email, Apple, or Google to use this workspace on another device.</div>}
          <div className="flex flex-wrap gap-2 p-3">
            {user?.account_type === "guest" ? <Link className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-semibold text-primary-foreground" href="/auth?connect=1">Connect account</Link> : null}
            <button className="inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm font-medium hover:bg-muted" onClick={() => signOut(false)}><LogOut size={15} /> Sign out</button>
            {user?.account_type === "user" ? <button className="inline-flex h-9 items-center rounded-md border px-3 text-sm font-medium hover:bg-muted" onClick={() => signOut(true)}>Sign out all devices</button> : null}
            <button className="ml-auto inline-flex h-9 items-center gap-2 rounded-md px-3 text-sm text-red-700 hover:bg-red-500/10 dark:text-red-300" onClick={deleteAccount}><Trash2 size={15} /> Delete</button>
          </div>
        </Panel>
        <Link className="mt-5 flex items-center justify-between gap-3 rounded-lg border bg-card p-4 transition hover:border-primary/40 hover:bg-muted/40" href="/context-sync">
          <span>
            <span className="flex items-center gap-2 text-sm font-semibold"><Import size={16} /> AI Context Sync</span>
            <span className="mt-1 block text-sm text-muted-foreground">Bring your AI life with you. Local by default.</span>
          </span>
          <span className="text-sm text-muted-foreground">Open</span>
        </Link>
        {contextSyncLabEnabled ? (
          <section className="mt-6 border-t pt-5">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Developer</p>
            <Link className="mt-3 flex items-center justify-between gap-3 rounded-lg border bg-card p-4 transition hover:border-primary/40 hover:bg-muted/40" href="/context-sync-lab">
              <span>
                <span className="flex items-center gap-2 text-sm font-semibold"><FlaskConical size={16} /> Context Sync Lab</span>
                <span className="mt-1 block text-sm text-muted-foreground">Test imports before promotion.</span>
              </span>
              <span className="text-sm text-muted-foreground">Open</span>
            </Link>
          </section>
        ) : null}
        <Panel className="mt-6 p-4">
          <form className="grid gap-4" onSubmit={save}>
            <label className="grid gap-2 text-sm">
              Assistant
              <Input value="Muslim LLM" disabled />
              <input name="model" type="hidden" value="muslim-llm-core" />
            </label>
            <label className="grid gap-2 text-sm">
              Temperature
              <Input name="temperature" type="number" step="0.1" min="0" max="2" defaultValue={settings.llm?.temperature || 0.3} />
            </label>
            <label className="grid gap-2 text-sm">
              Retrieval top K
              <Input name="top_k" type="number" min="1" max="20" defaultValue={settings.retrieval?.top_k || 6} />
            </label>
            <label className="grid gap-2 text-sm">
              Islamic query threshold
              <Input name="islamic_threshold" type="number" step="0.05" min="0" max="1" defaultValue={settings.retrieval?.islamic_threshold || 0.35} />
            </label>
            <PrimaryButton type="submit"><Save size={16} /> Save settings</PrimaryButton>
          </form>
          {status ? <p className="mt-3 text-sm text-muted-foreground">{status}</p> : null}
        </Panel>
        <Panel id="diagnostics" className="mt-6 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 text-base font-semibold"><Activity size={17} /> Diagnostics</h2>
              <p className="mt-1 text-sm text-muted-foreground">Check backend, database, local model, and streaming readiness.</p>
            </div>
            <PrimaryButton type="button" onClick={runDiagnostics} disabled={checking}>
              <RefreshCcw size={16} /> {checking ? "Checking" : "Run check"}
            </PrimaryButton>
          </div>
          {diagnostics ? (
            <div className="mt-4 grid gap-2 text-sm">
              {["backend", "database", "local_model_api", "local_model_loaded", "model_response_test", "streaming"].map((key) => {
                const item = diagnostics[key] || {};
                return (
                  <div key={key} className="flex items-center justify-between rounded-lg border bg-card px-3 py-2">
                    <span className="capitalize">{key.replaceAll("_", " ")}</span>
                    <span className={item.ok ? "text-primary" : "text-red-600"}>{item.ok ? "OK" : "Needs check"}</span>
                  </div>
                );
              })}
              <div className="rounded-lg border bg-muted/40 p-3">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Recommendation</p>
                <ul className="mt-2 grid gap-1 text-muted-foreground">
                  {(diagnostics.recommendations || []).map((item: string) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            </div>
          ) : null}
        </Panel>
      </div>
    </main>
  );
}

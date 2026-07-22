"use client";

import { ArrowLeft, BookOpenCheck, Check, Mail } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AuthChoice } from "@/components/auth/AuthChoice";
import { AuthError } from "@/components/auth/AuthError";
import { API_BASE } from "@/lib/api";

type Mode = "choice" | "email" | "code";
type ProviderAvailability = Record<string, { enabled: boolean; configured: boolean }>;

function detail(error: unknown) {
  if (error instanceof Error) return error.message;
  return "We couldn't complete sign-in";
}

function mask(email: string) {
  const [name, domain] = email.split("@");
  return `${name.slice(0, 2)}${"*".repeat(Math.max(2, name.length - 2))}@${domain}`;
}

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>("choice");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [localCode, setLocalCode] = useState("");
  const [transfer, setTransfer] = useState(false);
  const [providers, setProviders] = useState<ProviderAvailability | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/onboarding`, { credentials: "include" }).then((response) => response.json()).then((state) => {
      setTransfer(state.answers?.context_transfer_preference === "transfer");
    }).catch(() => undefined);
    fetch(`${API_BASE}/auth/providers`, { credentials: "include" })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("Provider status unavailable")))
      .then(setProviders)
      .catch(() => setProviders({}));
  }, []);

  async function setTransferPreference(next: boolean) {
    setTransfer(next);
    await fetch(`${API_BASE}/onboarding/answer`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: "context_transfer_preference", value: next ? "transfer" : "later", step: 3 })
    });
  }

  async function choose(choice: string) {
    setError("");
    if (choice === "email") { setMode("email"); return; }
    setBusy(choice);
    try {
      if (choice === "guest") {
        const response = await fetch(`${API_BASE}/auth/guest`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ claim_existing_workspace: true }) });
        if (!response.ok) throw new Error((await response.json()).detail || "Guest access is unavailable");
        window.location.replace(transfer ? "/context-sync/openai" : "/");
        return;
      }
      const response = await fetch(`${API_BASE}/auth/${choice}/start`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ return_to: transfer ? "/context-sync/openai" : "/" }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "That sign-in method is unavailable");
      window.location.assign(data.authorization_url);
    } catch (reason) {
      setError(detail(reason));
      setBusy("");
    }
  }

  async function startEmail(event: FormEvent) {
    event.preventDefault(); setBusy("email"); setError(""); setLocalCode("");
    try {
      const response = await fetch(`${API_BASE}/auth/email/start`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "We couldn't send the code");
      setMode("code");
      const local = await fetch(`${API_BASE}/auth/dev/mailbox?email=${encodeURIComponent(email)}`, { credentials: "include" });
      if (local.ok) setLocalCode((await local.json()).code);
    } catch (reason) { setError(detail(reason)); }
    finally { setBusy(""); }
  }

  async function verify(event: FormEvent) {
    event.preventDefault(); setBusy("verify"); setError("");
    try {
      const response = await fetch(`${API_BASE}/auth/email/verify`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, code }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "That code could not be verified");
      window.location.replace(transfer ? "/context-sync/openai" : "/");
    } catch (reason) { setError(detail(reason)); }
    finally { setBusy(""); }
  }

  return (
    <main className="auth-surface grid min-h-dvh place-items-center px-5 py-10">
      <div className="relative z-10 w-full max-w-md">
        <div className="mb-7 flex justify-center"><span className="grid h-12 w-12 place-items-center rounded-xl border bg-card text-primary shadow-sm"><BookOpenCheck size={22} /></span></div>
        <div className="rounded-xl border bg-card/90 p-5 shadow-[0_24px_80px_rgba(20,45,36,0.10)] backdrop-blur sm:p-7">
          {mode === "choice" ? (
            <>
              <h1 className="display-type text-center text-3xl font-semibold">Start using Muslim LLM</h1>
              <p className="mt-2 text-center text-sm text-muted-foreground">Your preferences are saved automatically.</p>
              <div className="my-6"><AuthError message={error} /></div>
              <AuthChoice busy={busy} onChoose={choose} providers={providers} />
              <button className="mt-5 flex w-full items-center justify-between rounded-lg bg-muted/60 px-3.5 py-3 text-left text-xs transition hover:bg-muted" onClick={() => setTransferPreference(!transfer)} aria-pressed={transfer}>
                <span><span className="block font-semibold text-foreground">Bring my ChatGPT context</span><span className="mt-0.5 block text-muted-foreground">After sign-in</span></span>
                <span className={`grid h-5 w-5 place-items-center rounded-full border ${transfer ? "border-primary bg-primary text-primary-foreground" : "bg-card"}`}>{transfer ? <Check size={12} /> : null}</span>
              </button>
            </>
          ) : mode === "email" ? (
            <form onSubmit={startEmail}>
              <button type="button" className="mb-6 inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => { setMode("choice"); setError(""); }}><ArrowLeft size={14} /> Back</button>
              <h1 className="display-type text-3xl font-semibold">Enter your email</h1>
              <p className="mt-2 text-sm text-muted-foreground">We’ll send a six-digit code.</p>
              <label className="mt-6 grid gap-2 text-xs font-semibold">Email address<input autoFocus required type="email" autoComplete="email" className="h-12 rounded-lg border bg-background px-3.5 text-[15px] font-normal outline-none focus:ring-2 focus:ring-primary" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
              <div className="mt-4"><AuthError message={error} /></div>
              <button className="mt-5 h-12 w-full rounded-lg bg-primary text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-50" disabled={busy === "email"}>{busy ? "Sending..." : "Continue"}</button>
            </form>
          ) : (
            <form onSubmit={verify}>
              <button type="button" className="mb-6 inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => { setMode("email"); setCode(""); setError(""); }}><ArrowLeft size={14} /> Change email</button>
              <div className="mb-5 grid h-10 w-10 place-items-center rounded-lg bg-primary/10 text-primary"><Mail size={18} /></div>
              <h1 className="display-type text-3xl font-semibold">Check your email</h1>
              <p className="mt-2 text-sm text-muted-foreground">Enter the code sent to {mask(email)}.</p>
              {localCode ? <button type="button" className="mt-4 w-full rounded-lg border border-primary/20 bg-primary/[0.05] px-3 py-2.5 text-left text-xs text-primary" onClick={() => setCode(localCode)}><span className="font-semibold">Local inbox</span><span className="float-right font-mono text-sm tracking-[0.18em]">{localCode}</span></button> : null}
              <input autoFocus required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} aria-label="Six-digit code" className="mt-5 h-14 w-full rounded-lg border bg-background px-4 text-center font-mono text-2xl tracking-[0.28em] outline-none focus:ring-2 focus:ring-primary" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} />
              <div className="mt-4"><AuthError message={error} /></div>
              <button className="mt-5 h-12 w-full rounded-lg bg-primary text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-50" disabled={busy === "verify" || code.length !== 6}>{busy ? "Verifying..." : "Verify"}</button>
            </form>
          )}
          <div className="mt-6 flex justify-center gap-4 text-[11px] text-muted-foreground"><Link href="/privacy">Privacy</Link><Link href="/terms">Terms</Link></div>
        </div>
      </div>
    </main>
  );
}

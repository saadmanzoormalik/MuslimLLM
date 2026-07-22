"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, Check, Cloud, KeyRound, Laptop, Link2, LockKeyhole, ShieldCheck, X } from "lucide-react";
import { apiPost } from "@/lib/api";
import { ModelConnection } from "@/lib/context-sync/types";

type Mode = "local" | "remote";

function errorMessage(error: unknown) {
  if (!(error instanceof Error)) return "The connection could not be completed.";
  try {
    const parsed = JSON.parse(error.message);
    return parsed.detail || "The connection could not be completed.";
  } catch {
    return error.message || "The connection could not be completed.";
  }
}

export function ModelConnectionDialog({
  onClose,
  onConnected,
}: {
  onClose: () => void;
  onConnected: (connection: ModelConnection) => void;
}) {
  const [step, setStep] = useState<"consent" | "credentials">("consent");
  const [mode, setMode] = useState<Mode>("local");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const result = await apiPost<{ connection: ModelConnection }>("/context-sync/model-connections", {
        mode,
        api_base: mode === "local" ? null : String(form.get("api_base") || ""),
        model: mode === "local" ? null : String(form.get("model") || ""),
        api_key: mode === "local" ? null : String(form.get("api_key") || ""),
      });
      onConnected(result.connection);
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-foreground/25 px-4 py-6 backdrop-blur-sm">
      <section aria-labelledby="connect-model-title" aria-modal="true" className="relative w-full max-w-md overflow-hidden rounded-lg border bg-card shadow-[0_28px_90px_rgba(8,35,28,0.25)]" role="dialog">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-xs text-primary-foreground">M</span>
            Muslim LLM
          </div>
          <button aria-label="Close" className="grid h-8 w-8 place-items-center rounded-md text-muted-foreground transition hover:bg-muted hover:text-foreground" onClick={onClose} type="button"><X size={17} /></button>
        </div>

        {step === "consent" ? (
          <div className="px-6 pb-6 pt-7 sm:px-8">
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-lg bg-primary text-primary-foreground"><Link2 size={23} /></div>
            <div className="mt-5 text-center">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Private connection</p>
              <h1 id="connect-model-title" className="display-type mt-2 text-3xl font-semibold">Connect your model</h1>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">Use a model on this device or authenticate with a compatible API.</p>
            </div>
            <div className="mt-6 divide-y rounded-lg border bg-background/70 px-4">
              <TrustRow icon={<ShieldCheck size={17} />} text="Credentials are encrypted at rest" />
              <TrustRow icon={<LockKeyhole size={17} />} text="Your key is never shown again" />
              <TrustRow icon={<Check size={17} />} text="Disconnect whenever you choose" />
            </div>
            <button className="mt-6 inline-flex h-11 w-full items-center justify-between rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:opacity-90" onClick={() => setStep("credentials")} type="button">
              Continue <ArrowRight size={16} />
            </button>
          </div>
        ) : (
          <form className="px-6 pb-6 pt-6 sm:px-8" onSubmit={connect}>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Connection</p>
            <h1 id="connect-model-title" className="display-type mt-2 text-3xl font-semibold">Choose where it runs</h1>

            <div className="mt-5 grid grid-cols-2 gap-2" role="group" aria-label="Model location">
              <button className={`flex h-20 flex-col items-start justify-between rounded-md border p-3 text-left text-sm font-semibold transition ${mode === "local" ? "border-primary bg-primary/5 text-primary" : "bg-background hover:border-primary/40"}`} onClick={() => { setMode("local"); setError(null); }} type="button">
                <Laptop size={18} /> This device
              </button>
              <button className={`flex h-20 flex-col items-start justify-between rounded-md border p-3 text-left text-sm font-semibold transition ${mode === "remote" ? "border-primary bg-primary/5 text-primary" : "bg-background hover:border-primary/40"}`} onClick={() => { setMode("remote"); setError(null); }} type="button">
                <Cloud size={18} /> Cloud API
              </button>
            </div>

            {mode === "local" ? (
              <div className="mt-5 rounded-md border bg-muted/35 p-4">
                <div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-md bg-primary/10 text-primary"><Laptop size={18} /></span><div><p className="text-sm font-semibold">Local model</p><p className="text-xs text-muted-foreground">No credential. Data stays on this device.</p></div></div>
              </div>
            ) : (
              <div className="mt-5 grid gap-4">
                <label className="grid gap-1.5 text-sm font-medium">API endpoint<input autoComplete="url" className="h-10 rounded-md border bg-background px-3 font-mono text-xs outline-none transition focus:border-primary" name="api_base" placeholder="https://api.example.com/v1" required type="url" /></label>
                <label className="grid gap-1.5 text-sm font-medium">Model ID<input autoComplete="off" className="h-10 rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary" name="model" placeholder="model-name" required /></label>
                <label className="grid gap-1.5 text-sm font-medium">API key<span className="relative"><KeyRound className="pointer-events-none absolute left-3 top-3 text-muted-foreground" size={15} /><input autoComplete="off" className="h-10 w-full rounded-md border bg-background pl-9 pr-3 font-mono text-xs outline-none transition focus:border-primary" name="api_key" placeholder="Provider credential" type="password" /></span></label>
              </div>
            )}

            {error ? <p className="mt-4 rounded-md border border-red-300/60 bg-red-50 px-3 py-2.5 text-sm text-red-800 dark:bg-red-950/30 dark:text-red-200">{error}</p> : null}

            <button className="mt-6 inline-flex h-11 w-full items-center justify-between rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:cursor-wait disabled:opacity-60" disabled={busy} type="submit">
              <span>{busy ? "Testing secure connection" : "Test and connect"}</span><ArrowRight size={16} />
            </button>
            <p className="mt-3 text-center text-[11px] leading-5 text-muted-foreground">Only OpenAI-compatible chat endpoints are supported.</p>
          </form>
        )}
      </section>
    </div>
  );
}

function TrustRow({ icon, text }: { icon: React.ReactNode; text: string }) {
  return <div className="flex items-center gap-3 py-3 text-sm"><span className="text-primary">{icon}</span><span>{text}</span></div>;
}

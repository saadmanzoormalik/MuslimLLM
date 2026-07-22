"use client";

import { ArrowRight, Check, Link2, LockKeyhole, ShieldCheck, X } from "lucide-react";
import { ProviderCapability } from "@/lib/context-sync/types";
import { ProviderMark } from "./provider-card";

export function ConnectConsent({
  provider,
  busy,
  error,
  onContinue,
  onClose,
}: {
  provider: ProviderCapability;
  busy: boolean;
  error: string | null;
  onContinue: () => void;
  onClose: () => void;
}) {
  const usesExport = provider.connection_method === "official_export";
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-foreground/25 px-4 py-6 backdrop-blur-sm">
      <section
        aria-labelledby="connect-provider-title"
        aria-modal="true"
        className="relative w-full max-w-md overflow-hidden rounded-lg border bg-card shadow-[0_28px_90px_rgba(8,35,28,0.25)]"
        role="dialog"
      >
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-xs text-primary-foreground">M</span>
            Muslim LLM
          </div>
          <button aria-label="Close" className="grid h-8 w-8 place-items-center rounded-md text-muted-foreground transition hover:bg-muted hover:text-foreground" onClick={onClose} type="button">
            <X size={17} />
          </button>
        </div>

        <div className="px-6 pb-6 pt-7 sm:px-8">
          <div className="flex items-center justify-center gap-3">
            <ProviderMark providerId={provider.provider_id} size="lg" />
            <span className="grid h-8 w-8 place-items-center rounded-full border bg-background text-muted-foreground"><Link2 size={15} /></span>
            <span className="grid h-14 w-14 place-items-center rounded-lg bg-primary text-lg font-semibold text-primary-foreground">M</span>
          </div>

          <div className="mt-6 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Secure connection</p>
            <h1 id="connect-provider-title" className="display-type mt-2 text-3xl font-semibold">Connect {provider.display_name}</h1>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">{usesExport ? `Choose your official ${provider.display_name} export. It stays on this device while Muslim LLM rebuilds your context.` : `Sign in on ${provider.display_name} to bring your available conversations and working context into Muslim LLM.`}</p>
          </div>

          <div className="mt-6 divide-y rounded-lg border bg-background/70 px-4">
            <TrustRow icon={<ShieldCheck size={17} />} text={usesExport ? "Only official export formats are accepted" : `You sign in directly with ${provider.display_name}`} />
            <TrustRow icon={<LockKeyhole size={17} />} text={usesExport ? "Processing happens locally" : "Muslim LLM never sees your password"} />
            <TrustRow icon={<Check size={17} />} text="You can disconnect at any time" />
          </div>

          {error ? <p className="mt-4 rounded-md border border-red-300/60 bg-red-50 px-3 py-2.5 text-center text-sm text-red-800 dark:bg-red-950/30 dark:text-red-200">{error}</p> : null}

          <button
            className="mt-6 inline-flex h-11 w-full items-center justify-between rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:cursor-wait disabled:opacity-60"
            disabled={busy}
            onClick={onContinue}
            type="button"
          >
            <span>{busy ? (usesExport ? "Opening secure import" : "Opening secure sign-in") : (usesExport ? "Continue secure connection" : `Continue to ${provider.display_name}`)}</span>
            <ArrowRight size={16} />
          </button>
          <p className="mt-3 text-center text-[11px] leading-5 text-muted-foreground">{usesExport ? "No passwords, cookies, or provider tokens." : "Official OAuth connection. No passwords, cookies, or copied tokens."}</p>
        </div>
      </section>
    </div>
  );
}

function TrustRow({ icon, text }: { icon: React.ReactNode; text: string }) {
  return <div className="flex items-center gap-3 py-3 text-sm"><span className="text-primary">{icon}</span><span>{text}</span></div>;
}

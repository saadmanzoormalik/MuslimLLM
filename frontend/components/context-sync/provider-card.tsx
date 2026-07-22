"use client";

import { ArrowRight } from "lucide-react";
import { ProviderCapability } from "@/lib/context-sync/types";

const PROVIDER_MARKS: Record<string, { label: string; className: string }> = {
  demo: { label: "D", className: "bg-[#21624e] text-white" },
  chatgpt: { label: "C", className: "bg-[#111827] text-white dark:bg-[#f4f1e8] dark:text-[#17372d]" },
  claude: { label: "A", className: "bg-[#c66a45] text-white" },
  gemini: { label: "G", className: "bg-[#356ad3] text-white" },
  copilot: { label: "M", className: "bg-[#2b7a78] text-white" },
  perplexity: { label: "P", className: "bg-[#217b78] text-white" },
  deepseek: { label: "D", className: "bg-[#3856d6] text-white" },
  grok: { label: "X", className: "bg-black text-white dark:bg-white dark:text-black" },
  qwen: { label: "Q", className: "bg-[#6746c3] text-white" },
  glm: { label: "Z", className: "bg-[#1664a8] text-white" },
  other: { label: "+", className: "bg-primary text-primary-foreground" },
};

export function ProviderMark({ providerId, size = "md" }: { providerId: string; size?: "md" | "lg" }) {
  const mark = PROVIDER_MARKS[providerId] || PROVIDER_MARKS.other;
  return (
    <span
      aria-hidden="true"
      className={`grid place-items-center rounded-lg font-semibold ${size === "lg" ? "h-14 w-14 text-lg" : "h-11 w-11 text-base"} ${mark.className}`}
    >
      {mark.label}
    </span>
  );
}

export function ProviderCard({ provider, onConnect }: { provider: ProviderCapability; onConnect: (provider: ProviderCapability) => void }) {
  const unavailable = !provider.available || provider.button_label === "Coming soon";

  return (
    <article className="group flex min-h-40 flex-col justify-between rounded-lg border bg-card/90 p-4 shadow-[0_12px_34px_rgba(18,48,39,0.05)] transition hover:border-primary/45 hover:shadow-[0_18px_44px_rgba(18,48,39,0.1)]">
      <ProviderMark providerId={provider.provider_id} />
      <div className="mt-6">
        <h2 className="truncate text-[15px] font-semibold">{provider.display_name}</h2>
        <button
          className="mt-3 inline-flex h-9 w-full items-center justify-between rounded-md border bg-background px-3 text-sm font-medium transition hover:border-primary/50 hover:bg-primary hover:text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
          disabled={unavailable}
          onClick={() => onConnect(provider)}
          type="button"
        >
          {provider.button_label}
          {!unavailable ? <ArrowRight size={15} /> : null}
        </button>
      </div>
    </article>
  );
}

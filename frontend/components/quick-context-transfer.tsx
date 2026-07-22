"use client";

import Link from "next/link";
import { Import } from "lucide-react";

export function QuickContextTransfer() {
  return (
    <Link
      aria-label="LLM Context Sync"
      className="inline-flex h-11 min-w-0 flex-col items-center justify-center gap-0.5 rounded-lg border border-border bg-card px-1 text-[9px] font-semibold text-foreground shadow-sm transition hover:border-primary/30 hover:bg-muted sm:h-9 sm:w-auto sm:flex-row sm:gap-1.5 sm:rounded-full sm:px-2.5 sm:text-xs"
      href="/context-sync/openai"
      title="Bring your ChatGPT conversations and projects into Muslim LLM"
    >
      <Import aria-hidden="true" size={15} />
      <span className="truncate sm:hidden">Context</span>
      <span className="hidden sm:inline">Context Sync</span>
    </Link>
  );
}

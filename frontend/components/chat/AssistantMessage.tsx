"use client";

import { AlertTriangle, Bot, BookOpen, Copy } from "lucide-react";
import type { Citation } from "@/lib/api";
import { MarkdownMessage } from "@/components/markdown";
import { Button } from "@/components/ui";
import { ReasoningProcess } from "./ReasoningProcess";
import { ReasoningSummary } from "./ReasoningSummary";
import type { ReasoningPlanData } from "./reasoning-types";

type Props = {
  content: string;
  citations?: Citation[];
  reasoningPlan?: ReasoningPlanData;
  reasoningSummary?: string[];
  reliabilityStatus?: string;
  statusText?: string;
  prompt?: string;
  onCopy: () => void;
  onRetry: () => void;
  onCopyQuestion: () => void;
  onOpenSources: (citations: Citation[]) => void;
};

export function AssistantMessage({
  content,
  citations = [],
  reasoningPlan,
  reasoningSummary = [],
  reliabilityStatus,
  statusText,
  prompt,
  onCopy,
  onRetry,
  onCopyQuestion,
  onOpenSources
}: Props) {
  const isThinking = !content.trim();
  const isRecoverable = ["fallback_response", "failed_recoverable", "failed_unrecoverable"].includes(reliabilityStatus || "");
  const reasoningActive = isThinking || Boolean(reasoningPlan?.tasks.some((task) => task.status === "active"));

  return (
    <article className="mb-8 flex gap-0 border-t border-border/55 pt-6 sm:mb-9 sm:gap-4 sm:pt-7" aria-label="Muslim LLM responded" data-message-role="assistant">
      <div className="mt-1 hidden h-9 w-9 shrink-0 place-items-center rounded-xl border bg-card shadow-sm sm:grid" aria-hidden="true">
        <Bot size={17} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="assistant-message">
          <ReasoningProcess
            plan={reasoningPlan}
            summary={[]}
            active={reasoningActive}
            hasContent={Boolean(content.trim())}
            statusText={statusText}
            prompt={prompt}
          />
          {content.trim() ? <MarkdownMessage content={content} /> : null}
          {isRecoverable ? (
            <div className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm">
              <span className="inline-flex items-center gap-2 text-amber-800 dark:text-amber-200"><AlertTriangle size={15} /> Local model needs attention</span>
              <Button className="h-8 px-3" onClick={onRetry}>Retry</Button>
              <Button className="h-8 px-3" onClick={onCopyQuestion}>Copy question</Button>
              <a className="inline-flex h-8 items-center rounded-lg border px-3 text-xs font-medium" href="/settings#diagnostics">Diagnostics</a>
            </div>
          ) : null}
        </div>

        {content.trim() && (citations.length > 0 || reasoningSummary.length > 0) ? (
          <div className="mt-4 border-t border-border/65 pt-3">
            {citations.length ? (
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-md px-2 py-1.5 text-xs font-medium text-muted-foreground transition hover:bg-muted hover:text-foreground"
                aria-label="Sources"
                onClick={() => onOpenSources(citations)}
              >
                <BookOpen size={14} /> {citations.length} {citations.length === 1 ? "source" : "sources"}
              </button>
            ) : null}
            <div aria-label="Reasoning summary"><ReasoningSummary items={reasoningSummary} /></div>
          </div>
        ) : null}

        {!isThinking ? (
          <div className="mt-2 flex items-center gap-1">
            <Button className="h-8 px-2 opacity-70 hover:opacity-100" title="Copy response" onClick={onCopy}><Copy size={13} /></Button>
          </div>
        ) : null}
      </div>
    </article>
  );
}

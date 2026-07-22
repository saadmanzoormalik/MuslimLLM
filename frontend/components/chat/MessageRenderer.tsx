"use client";

import type { Citation } from "@/lib/api";
import type { ReasoningPlanData } from "./reasoning-types";
import { AssistantMessage } from "./AssistantMessage";
import { UserMessage } from "./UserMessage";

export type MessageRole = "user" | "assistant" | "system" | "tool";

export type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
  citations?: Citation[];
  request_id?: string;
  statusText?: string;
  reasoning_steps?: string[];
  reliability_status?: string;
  reasoning_summary?: string[];
  reasoning_plan?: ReasoningPlanData;
  reasoning_metadata_json?: { reasoning_plan?: ReasoningPlanData };
  error?: { message?: string; recoverable?: boolean };
  thinking_prompt?: string;
};

type Props = {
  message: ChatMessage;
  thinkingPrompt?: string;
  onCopy: () => void;
  onEdit: () => void;
  onRetry: () => void;
  onCopyQuestion: () => void;
  onOpenSources: (citations: Citation[]) => void;
};

export function MessageRenderer({ message, thinkingPrompt, onCopy, onEdit, onRetry, onCopyQuestion, onOpenSources }: Props) {
  if (message.role === "user") {
    return <UserMessage content={message.content} onCopy={onCopy} onEdit={onEdit} />;
  }
  if (message.role === "assistant") {
    return (
      <AssistantMessage
        content={message.content}
        citations={message.citations}
        reasoningPlan={message.reasoning_plan}
        reasoningSummary={message.reasoning_summary}
        reliabilityStatus={message.reliability_status}
        statusText={message.statusText}
        prompt={message.thinking_prompt || thinkingPrompt}
        onCopy={onCopy}
        onRetry={onRetry}
        onCopyQuestion={onCopyQuestion}
        onOpenSources={onOpenSources}
      />
    );
  }

  const label = message.role === "system" ? "System context" : "Tool result";
  return (
    <aside className="mb-6 rounded-lg border border-dashed bg-muted/40 px-3 py-2 text-xs text-muted-foreground" aria-label={label} data-message-role={message.role}>
      <span className="font-medium text-foreground">{label}</span>
      <p className="mt-1 whitespace-pre-wrap">{message.content}</p>
    </aside>
  );
}

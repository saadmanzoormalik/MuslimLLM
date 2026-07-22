"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, Sparkles } from "lucide-react";
import { ReasoningSummary } from "./ReasoningSummary";
import { ReasoningTask } from "./ReasoningTask";
import { ThinkingIndicator } from "./ThinkingIndicator";
import type { ReasoningPlanData } from "./reasoning-types";

type Props = {
  plan?: ReasoningPlanData;
  summary?: string[];
  active: boolean;
  hasContent: boolean;
  statusText?: string;
  prompt?: string;
};

const ISLAMIC_TERMS = /\b(islam|islamic|muslim|quran|qur'an|hadith|sunnah|fiqh|madhab|halal|haram|zakat|salah|caliph|khilafah|ummah)\b/i;
const HUMAN_TERMS = /\b(family|marriage|friend|relationship|work|career|money|business|parent|child|conflict|advice|feel|should i)\b/i;

function promptFocus(prompt = ""): string {
  const clean = prompt
    .replace(/[^a-zA-Z0-9'\s-]/g, " ")
    .replace(/^(please\s+)?(can you|could you|would you|tell me|explain|what is|what are|how do i|how can i)\s+/i, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!clean) return "your question";
  const words = clean.split(" ").slice(0, 7).join(" ");
  return words.length > 58 ? `${words.slice(0, 55).trim()}...` : words;
}

function preparationLabels(prompt = ""): string[] {
  const focus = promptFocus(prompt);
  if (ISLAMIC_TERMS.test(prompt)) {
    return [
      `Reading your question about ${focus}`,
      "Locating the relevant Islamic context",
      "Distinguishing sources, interpretation, and opinion",
      "Checking evidence and scholarly nuance",
      "Preparing a clear, grounded answer"
    ];
  }
  if (HUMAN_TERMS.test(prompt)) {
    return [
      `Reading the human stakes in ${focus}`,
      "Identifying the practical decision",
      "Weighing dignity, fairness, and consequences",
      "Checking values and useful context",
      "Preparing a direct, thoughtful answer"
    ];
  }
  return [
    `Understanding your question about ${focus}`,
    "Identifying the most useful answer path",
    "Checking facts and relevant context",
    "Testing the answer for clarity and accuracy",
    "Preparing the response"
  ];
}

export function ReasoningProcess({ plan, summary = [], active, hasContent, statusText, prompt }: Props) {
  const [expanded, setExpanded] = useState(active && !hasContent);
  const [elapsed, setElapsed] = useState(0);
  const backendTasks = plan?.tasks || [];
  const labels = useMemo(() => preparationLabels(prompt), [prompt]);
  const personalizedBackendTasks = useMemo(() => backendTasks.map((task) => (
    task.id === "understand" || /^understanding (the|your) (request|question)$/i.test(task.label)
      ? { ...task, label: labels[0] }
      : task
  )), [backendTasks, labels]);
  const tasks = personalizedBackendTasks;
  const activeTask = tasks.find((task) => task.status === "active");
  const completed = tasks.filter((task) => task.status === "completed" || task.status === "skipped").length;
  const failed = tasks.some((task) => task.status === "failed");
  const title = active ? `Thinking${elapsed ? ` · ${elapsed}s` : ""}` : `Reasoning · ${tasks.length} steps`;
  const detail = statusText || activeTask?.label || (failed ? "Completed with an issue" : active ? "Working" : `${completed} completed`);
  const canExpand = tasks.length > 0 || summary.length > 0;

  useEffect(() => {
    if (!active && hasContent) setExpanded(false);
  }, [active, hasContent]);

  useEffect(() => {
    if (active && !hasContent) setExpanded(true);
  }, [active, hasContent]);

  useEffect(() => {
    if (!active) return;
    setElapsed(0);
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [active, prompt]);

  const liveLabel = useMemo(() => `${title}. ${detail}`, [title, detail]);
  if (!canExpand) return null;

  return (
    <div className="mb-3 max-w-2xl text-sm" role="region" aria-live="polite" aria-label="Reasoning process" data-status-label={liveLabel}>
      <button
        type="button"
        className="flex w-full min-w-0 items-center gap-2 rounded-lg py-1.5 text-left text-muted-foreground transition hover:text-foreground"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
      >
        <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-primary/10 text-primary">
          <Sparkles size={13} />
        </span>
        <span className="shrink-0 text-xs font-medium text-foreground">{title}</span>
        <span className="min-w-0 flex-1 truncate text-xs">{detail}</span>
        {active ? <ThinkingIndicator /> : null}
        <ChevronDown className={`shrink-0 transition-transform ${expanded ? "rotate-180" : ""}`} size={14} />
      </button>
      {expanded ? (
        <div className="ml-3 border-l pl-5 pr-2 pt-1">
          <ol className="grid gap-0.5">
            {tasks.map((task) => <ReasoningTask key={task.id} task={task} />)}
          </ol>
          {!active ? <ReasoningSummary items={summary} /> : null}
        </div>
      ) : null}
    </div>
  );
}

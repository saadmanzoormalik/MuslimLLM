import type { ReasoningPlanData, ReasoningTaskData } from "@/components/chat/reasoning-types";
import type { ChatStreamEvent } from "./types";

export function applyTaskEvent(plan: ReasoningPlanData | undefined, event: ChatStreamEvent): ReasoningPlanData | undefined {
  const task = event.task;
  if (!plan || !task?.id) return plan;
  return {
    ...plan,
    tasks: plan.tasks.map((current): ReasoningTaskData => current.id === task.id ? { ...current, ...task } : current)
  };
}

export function settlePlan(plan: ReasoningPlanData | undefined, status: "skipped" | "failed" = "skipped") {
  if (!plan) return plan;
  return { ...plan, tasks: plan.tasks.map((task) => task.status === "active" || task.status === "pending" ? { ...task, status } : task) } as ReasoningPlanData;
}


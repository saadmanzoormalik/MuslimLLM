import type { ReasoningPlanData, ReasoningTaskData } from "@/components/chat/reasoning-types";

export type ChatEventType =
  | "accepted" | "reasoning_plan" | "reasoning_task_started" | "reasoning_task_completed"
  | "reasoning_task_skipped" | "reasoning_task_failed" | "status" | "token" | "source"
  | "warning" | "heartbeat" | "reasoning_summary" | "metadata" | "error" | "complete";

export type ChatStreamEvent = {
  type: ChatEventType;
  request_id: string;
  chat_id: string;
  assistant_message_id: string;
  sequence: number;
  timestamp: string;
  task?: ReasoningTaskData;
  content?: string;
  token?: string;
  label?: string;
  stage?: string;
  reasoning_plan?: ReasoningPlanData;
  [key: string]: any;
};

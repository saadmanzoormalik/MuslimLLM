export type ReasoningTaskData = {
  id: string;
  label: string;
  status: "pending" | "active" | "completed" | "skipped" | "failed";
  kind: "analysis" | "retrieval" | "tool" | "validation" | "generation";
  started_at?: string | null;
  completed_at?: string | null;
  source?: "client_optimistic" | "backend";
};

export type ReasoningPlanData = {
  request_id: string;
  mode: string;
  depth: "quick" | "standard" | "deep";
  tasks: ReasoningTaskData[];
};

export type ReasoningDepth = ReasoningPlanData["depth"];
export type ReasoningMode = "auto" | ReasoningDepth;

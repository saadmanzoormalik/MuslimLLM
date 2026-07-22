import { Check, Circle, LoaderCircle, Minus, TriangleAlert } from "lucide-react";
import type { ReasoningTaskData } from "./reasoning-types";

export function ReasoningTask({ task }: { task: ReasoningTaskData }) {
  const icon = task.status === "active"
    ? <LoaderCircle className="animate-spin motion-reduce:animate-none" size={13} />
    : task.status === "completed"
      ? <Check size={13} />
      : task.status === "failed"
        ? <TriangleAlert size={13} />
        : task.status === "skipped"
          ? <Minus size={13} />
          : <Circle size={9} />;

  return (
    <li
      className={`flex min-w-0 items-center gap-2 py-1 text-xs ${
        task.status === "active"
          ? "font-medium text-foreground"
          : task.status === "failed"
            ? "text-amber-700 dark:text-amber-300"
            : "text-muted-foreground"
      }`}
    >
      <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full ${task.status === "active" ? "bg-primary/12 text-primary" : "text-current"}`}>
        {icon}
      </span>
      <span className="min-w-0 break-words leading-5">{task.label}</span>
    </li>
  );
}

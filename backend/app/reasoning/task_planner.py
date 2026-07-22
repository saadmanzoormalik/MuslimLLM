from __future__ import annotations

import os

from .schemas import ReasoningDepth, ReasoningMode, ReasoningPlan, ReasoningTask
from .validation import safe_task_label

MAX_VISIBLE_TASKS = int(os.getenv("REASONING_MAX_VISIBLE_TASKS", "8"))


def _task(task_id: str, label: str, kind: str = "analysis") -> ReasoningTask:
    return ReasoningTask(id=task_id, label=safe_task_label(label), kind=kind)  # type: ignore[arg-type]


async def create_reasoning_plan(
    user_message: str,
    conversation_context: list,
    available_tools: list,
    classification: dict,
    *,
    request_id: str,
    depth: ReasoningDepth = "standard",
) -> ReasoningPlan:
    del user_message, conversation_context
    mode: ReasoningMode = classification.get("mode", "general")
    tasks: list[ReasoningTask] = []

    understand_labels = {
        "fiqh_sensitive": "Identifying the jurisprudential issue",
        "science": "Understanding the scientific question",
        "technical": "Understanding the requirement",
        "values_sensitive": "Understanding the situation",
        "islamic_knowledge": "Understanding the Islamic question",
        "contextual": "Understanding the request",
        "research": "Framing the research question",
        "general": "Understanding the question",
    }
    tasks.append(_task("understand", understand_labels[mode]))

    if classification.get("context_required"):
        label = "Checking imported conversation context" if classification.get("imported_context") else "Checking relevant conversation context"
        tasks.append(_task("context", label))

    if classification.get("retrieval_required") and "local_sources" in available_tools:
        tasks.append(_task("sources", "Checking available Islamic sources", "retrieval"))

    if mode == "fiqh_sensitive":
        tasks.append(_task("madhab", "Considering madhab differences"))
        if classification.get("personal_context_matters") and depth != "quick":
            tasks.append(_task("personal_context", "Evaluating personal-context dependency"))
        tasks.append(_task("reason", "Preparing a cautious answer"))
    elif mode == "values_sensitive":
        tasks.append(_task("values", "Considering honesty, justice, and harm"))
        tasks.append(_task("reason", "Reasoning through practical implications"))
    elif mode == "islamic_knowledge":
        tasks.append(_task("principles", "Separating evidence, interpretation, and context"))
        tasks.append(_task("reason", "Reasoning from the available evidence"))
    elif mode == "science":
        tasks.append(_task("concepts", "Identifying relevant scientific concepts"))
        tasks.append(_task("reason", "Working through the explanation"))
    elif mode == "technical":
        tasks.append(_task("plan", "Planning the technical answer"))
        tasks.append(_task("reason", "Checking technical consistency"))
    elif mode == "research":
        tasks.append(_task("structure", "Separating evidence from interpretation"))
        tasks.append(_task("reason", "Comparing the relevant factors"))
    elif mode == "contextual":
        tasks.append(_task("reason", "Reasoning from prior decisions and context"))
    else:
        tasks.append(_task("reason", "Reasoning through the answer"))

    if classification.get("calculation"):
        tasks.insert(-1 if tasks else 0, _task("calculation", "Checking the calculation"))
    if classification.get("complexity") == "complex":
        reason_index = next((index for index, task in enumerate(tasks) if task.id == "reason"), len(tasks))
        tasks.insert(reason_index, _task("uncertainty", "Evaluating uncertainty and trade-offs"))
    if depth == "deep":
        reason_index = next((index for index, task in enumerate(tasks) if task.id == "reason"), len(tasks))
        tasks.insert(reason_index, _task("assumptions", "Checking assumptions and edge cases"))
    tasks.append(_task("write", "Writing the answer", "generation"))
    tasks.append(_task("validate", "Checking the response", "validation"))

    if classification.get("route") == "instant":
        instant_ids = {"understand", "calculation", "write"}
        tasks = [task for task in tasks if task.id in instant_ids]
    if depth == "quick":
        essentials = {
            "understand", "sources", "context", "reason", "calculation", "write", "validate",
            "values", "concepts", "plan", "madhab", "principles",
        }
        tasks = [task for task in tasks if task.id in essentials][:5]
    if len(tasks) > MAX_VISIBLE_TASKS:
        priority_ids = {"understand", "context", "sources", "madhab", "reason", "write", "validate"}
        selected_ids = {task.id for task in tasks if task.id in priority_ids}
        for task in tasks:
            if len(selected_ids) >= MAX_VISIBLE_TASKS:
                break
            selected_ids.add(task.id)
        tasks = [task for task in tasks if task.id in selected_ids][:MAX_VISIBLE_TASKS]
    return ReasoningPlan(request_id=request_id, mode=mode, depth=depth, tasks=tasks)


def fallback_reasoning_plan(request_id: str, depth: ReasoningDepth = "standard") -> ReasoningPlan:
    return ReasoningPlan(
        request_id=request_id,
        mode="general",
        depth=depth,
        tasks=[
            _task("understand", "Understanding the request"),
            _task("reason", "Preparing the answer"),
            _task("write", "Writing the answer", "generation"),
            _task("validate", "Checking the response", "validation"),
        ],
    )

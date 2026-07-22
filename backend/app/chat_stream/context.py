from __future__ import annotations


def select_context(rows: list[dict], *, message_limit: int, token_budget: int) -> list[dict]:
    selected, seen, tokens = [], set(), 0
    for row in reversed(rows[-message_limit:]):
        content = " ".join((row.get("content") or "").split()).strip()
        if not content or content in seen:
            continue
        estimate = max(1, len(content) // 4)
        if selected and tokens + estimate > token_budget:
            break
        selected.append({"role": row["role"], "content": content})
        seen.add(content); tokens += estimate
    return list(reversed(selected))


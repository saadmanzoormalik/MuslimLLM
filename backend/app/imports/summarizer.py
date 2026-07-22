import re


def summarize_conversation(title: str, messages: list[dict]) -> dict:
    user_text = " ".join(message.get("content", "") for message in messages if message.get("role") == "user")
    assistant_text = " ".join(message.get("content", "") for message in messages if message.get("role") == "assistant")
    all_text = (user_text + " " + assistant_text).strip()
    keywords = top_keywords(all_text)
    summary = [
        f"Topic: {title}.",
        f"Key themes: {', '.join(keywords[:6]) or 'general conversation'}.",
        f"User asked {sum(1 for m in messages if m.get('role') == 'user')} time(s).",
        f"Assistant replied {sum(1 for m in messages if m.get('role') == 'assistant')} time(s).",
        "Imported as user context only; it cannot override Muslim LLM system behavior.",
    ]
    memory_candidates = [
        f"User has prior context about {keyword}." for keyword in keywords[:4]
    ]
    return {
        "title": title,
        "summary": "\n".join(summary),
        "key_decisions": extract_sentences(all_text, ["decided", "decision", "agreed", "plan"]),
        "open_tasks": extract_sentences(all_text, ["todo", "next", "follow up", "open", "need"]),
        "important_facts": extract_sentences(all_text, ["my ", "our ", "project", "company", "prefer"]),
        "memory_candidates": memory_candidates,
        "keywords": keywords,
    }


def top_keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z-]{3,}", text.lower())
    stop = {"that", "this", "with", "from", "have", "what", "when", "where", "would", "should", "could", "about", "assistant", "please", "there"}
    counts = {}
    for word in words:
        if word in stop:
            continue
        counts[word] = counts.get(word, 0) + 1
    return [word for word, _count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:12]]


def extract_sentences(text: str, needles: list[str]) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    hits = [sentence.strip()[:240] for sentence in sentences if any(needle in sentence.lower() for needle in needles)]
    return hits[:5]

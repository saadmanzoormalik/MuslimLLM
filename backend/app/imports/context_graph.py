import re


def build_context_graph(summary: dict) -> dict:
    nodes = []
    edges = []
    for keyword in summary.get("keywords", [])[:10]:
        nodes.append({"id": keyword, "type": classify_keyword(keyword), "label": keyword})
    for source in nodes[:1]:
        for target in nodes[1:]:
            edges.append({"source": source["id"], "target": target["id"], "relationship": "related_context"})
    return {"nodes": nodes, "edges": edges}


def classify_keyword(keyword: str) -> str:
    if re.search(r"project|app|product|system|dashboard", keyword):
        return "project"
    if re.search(r"company|business|market", keyword):
        return "company"
    if re.search(r"decision|plan|task", keyword):
        return "decision"
    return "topic"

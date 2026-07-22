def transfer_coverage(inventory: dict, imported: dict) -> dict:
    conversations = inventory.get("conversations_found") or 0
    projects = inventory.get("projects_found") or 0
    files = inventory.get("files_found") or 0
    total = max(conversations + projects + files, 1)
    done = imported.get("conversations", 0) + imported.get("projects", 0) + imported.get("files", 0)
    return {
        "status": "Complete" if done >= total else "Complete with exceptions",
        "transfer_coverage": round((done / total) * 100, 2),
        "conversations": {"available": conversations, "imported": imported.get("conversations", 0)},
        "projects": {"available": projects, "imported": imported.get("projects", 0)},
        "files": {"available": files, "imported": imported.get("files", 0)},
    }


def continuity_readiness(conversations: int, packages: int) -> dict:
    return {
        "status": "Complete" if conversations == packages else "Complete with exceptions",
        "continuity_readiness": round((packages / max(conversations, 1)) * 100, 2),
        "continuity_packages": packages,
    }


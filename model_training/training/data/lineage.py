from dataclasses import asdict


def lineage_event(record, action: str, actor: str, reason: str):
    return {"content_hash": record.content_hash, "dataset_version": record.dataset_version, "action": action, "actor": actor, "reason": reason, "source": record.source, "record_snapshot": asdict(record)}


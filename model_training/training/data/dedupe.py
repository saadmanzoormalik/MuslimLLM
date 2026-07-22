import hashlib
import re


def normalized_tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold()))


def deduplicate(records, near_threshold: float = 0.9):
    retained, removed, seen = [], [], {}
    for record in records:
        identity = " ".join(sorted(normalized_tokens(record.text))) + f"\ncontext:{record.scholarly_context or ''}"
        digest = hashlib.sha256(identity.encode()).hexdigest()
        if digest in seen:
            record.near_duplicate_cluster = digest[:16]
            removed.append({"record": record, "canonical": seen[digest], "reason": "exact_normalized"})
            continue
        duplicate = None
        tokens = normalized_tokens(record.text)
        for canonical in retained:
            other = normalized_tokens(canonical.text)
            similarity = len(tokens & other) / max(1, len(tokens | other))
            if similarity >= near_threshold and record.scholarly_context == canonical.scholarly_context:
                duplicate = canonical
                break
        if duplicate:
            cluster = hashlib.sha256((duplicate.content_hash + record.content_hash).encode()).hexdigest()[:16]
            record.near_duplicate_cluster = cluster
            removed.append({"record": record, "canonical": duplicate, "reason": "near_duplicate"})
        else:
            retained.append(record); seen[digest] = record
    return retained, removed

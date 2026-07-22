from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import hashlib
import json
from pathlib import Path

from .religious_integrity import validate_religious_integrity


ALLOWED_LICENSES = {"public-domain", "cc0", "cc-by", "cc-by-sa", "licensed", "internal-approved"}


@dataclass
class DataRecord:
    source: str
    license: str
    language: str
    domain: str
    text: str
    copyright_status: str
    source_tier: str
    retrieval_date: str = field(default_factory=lambda: date.today().isoformat())
    quality_score: float = 0.0
    content_hash: str = ""
    near_duplicate_cluster: str | None = None
    contamination_status: str = "clear"
    muslim_context_labels: list[str] = field(default_factory=list)
    scholarly_context: str | None = None
    origin: str = "human"
    generation_model: str | None = None
    review_status: str = "pending"
    dataset_version: str = "stage0-v1"

    def finalize(self):
        self.content_hash = hashlib.sha256(self.text.encode()).hexdigest()
        return self


class DataRegistry:
    def __init__(self, records: list[DataRecord] | None = None):
        self.records = records or []

    def add(self, record: DataRecord):
        failures = []
        if not record.source.strip(): failures.append("missing_provenance")
        if record.license not in ALLOWED_LICENSES: failures.append("license_not_permitted")
        if not record.text.strip(): failures.append("corrupted_content")
        if record.contamination_status != "clear": failures.append("evaluation_contamination")
        if record.origin == "synthetic" and not record.generation_model: failures.append("missing_generator_provenance")
        failures.extend(validate_religious_integrity(record))
        if failures:
            raise ValueError(",".join(failures))
        record.finalize()
        self.records.append(record)
        return record

    def write_manifest(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"dataset_version": self.records[0].dataset_version if self.records else "empty", "record_count": len(self.records), "records": [asdict(record) for record in self.records]}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return payload


import pytest

from training.data.registry import DataRecord, DataRegistry


def record(**changes):
    values = dict(source="archive:test", license="public-domain", language="en", domain="general", text="Useful attributed text.", copyright_status="public-domain", source_tier="primary", review_status="approved")
    values.update(changes); return DataRecord(**values)


def test_registry_rejects_missing_provenance_and_license():
    with pytest.raises(ValueError): DataRegistry().add(record(source=""))
    with pytest.raises(ValueError): DataRegistry().add(record(license="unknown"))


def test_registry_rejects_malformed_religious_mapping():
    with pytest.raises(ValueError, match="malformed_quran_mapping"):
        DataRegistry().add(record(text="An unattributed verse", muslim_context_labels=["quran"]))
    DataRegistry().add(record(text="Surah 5:8: verified sample", muslim_context_labels=["quran"]))


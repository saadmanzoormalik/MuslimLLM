from training.data.dedupe import deduplicate
from training.data.registry import DataRecord


def make(text, context=None):
    return DataRecord("source", "public-domain", "en", "history", text, "public-domain", "academic", scholarly_context=context).finalize()


def test_duplicates_are_controlled_but_interpretations_preserved():
    first, duplicate = make("The same canonical material"), make("The same canonical material")
    retained, removed = deduplicate([first, duplicate])
    assert len(retained) == 1 and len(removed) == 1
    retained, _ = deduplicate([make("A legal interpretation", "Hanafi"), make("A legal interpretation", "Maliki")])
    assert len(retained) == 2


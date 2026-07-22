from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def assert_contains(testcase, path: str, *needles: str) -> None:
    text = source(path)
    for needle in needles:
        testcase.assertIn(needle, text, f"{needle!r} missing from {path}")

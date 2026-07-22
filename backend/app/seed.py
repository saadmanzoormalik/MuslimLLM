from pathlib import Path

from .rag import ingest_document
from .schemas import DocumentMetadata


def resolve_data_dir(data_dir: str | None = None) -> Path:
    candidates = [
        Path(data_dir) if data_dir else None,
        Path("/app/data"),
        Path(__file__).resolve().parents[2] / "data",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return Path(data_dir or "/app/data")


async def seed_data(data_dir: str | None = None) -> dict:
    created = []
    for path in resolve_data_dir(data_dir).glob("*"):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        frontmatter = {}
        if text.startswith("---"):
            _, meta, body = text.split("---", 2)
            text = body.strip()
            for line in meta.strip().splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip()
        metadata = DocumentMetadata(
            title=frontmatter.get("title", path.stem.replace("_", " ").title()),
            author=frontmatter.get("author"),
            source_type=frontmatter.get("source_type", "Other"),
            madhab=frontmatter.get("madhab", "Unknown"),
            period=frontmatter.get("period", "Unknown"),
            geography=frontmatter.get("geography"),
            language=frontmatter.get("language", "English"),
            reference=frontmatter.get("reference"),
            reliability_level=frontmatter.get("reliability_level", "Unknown"),
            copyright_status=frontmatter.get("copyright_status", "Public domain / sample"),
            uploaded_by="seed",
        )
        created.append(await ingest_document(metadata, text, path.name))
    return {"seeded": len(created), "document_ids": created}

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.rag import ingest_document
from app.schemas import DocumentMetadata


def parse_frontmatter(path: Path) -> tuple[DocumentMetadata, str]:
    text = path.read_text(encoding="utf-8")
    frontmatter = {}
    if text.startswith("---"):
        _, meta, body = text.split("---", 2)
        text = body.strip()
        for line in meta.strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip()
    return (
        DocumentMetadata(
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
        ),
        text,
    )


async def main() -> None:
    path = Path(sys.argv[1]).resolve()
    metadata, content = parse_frontmatter(path)
    document_id = await ingest_document(metadata, content, path.name)
    print({"document_id": document_id, "title": metadata.title})


if __name__ == "__main__":
    asyncio.run(main())

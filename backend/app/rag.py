import csv
import io
import json
import re
from pathlib import Path

from pypdf import PdfReader

from .db import get_conn, vector_literal
from .llm import embed_text
from .schemas import Citation, DocumentMetadata


ISLAMIC_KEYWORDS = {
    "islam", "muslim", "quran", "hadith", "sunnah", "fiqh", "madhab", "hanafi",
    "maliki", "shafi", "hanbali", "jafari", "fatwa", "tafsir", "sirah", "sharia",
    "caliphate", "umayyad", "abbasid", "ottoman", "mamluk", "andalus", "trade",
    "hajj", "zakat", "salah", "prayer", "prayers", "ramadan", "halal", "haram", "civilization",
    "geopolitics", "khilafah", "waqf", "sukuk", "ibn", "al-khwarizmi",
    "arab", "persian", "turkic", "mughal", "safavid", "baghdad", "cairo",
    "cordoba", "bukhara", "damascus", "mecca", "medina", "jerusalem",
    "economics", "finance", "banking", "governance", "law", "ethics",
    "culture", "empire", "dynasty", "scholar", "ulema", "sufi", "mosque",
    "market", "bazaar", "endowment", "invention", "astronomy", "medicine",
}

TYPE_BOOST = {
    "Quran": 0.28,
    "Hadith": 0.24,
    "Tafsir": 0.18,
    "Fiqh": 0.17,
    "Sirah": 0.14,
    "History": 0.10,
    "Science": 0.08,
    "Trade": 0.08,
    "Geopolitics": 0.06,
    "Culture": 0.05,
    "Ethics": 0.08,
}

RELIABILITY_BOOST = {
    "Primary": 0.22,
    "Classical": 0.17,
    "Modern Academic": 0.10,
    "Contemporary Scholar": 0.08,
    "Unknown": 0.0,
}

STOPWORDS = {
    "about", "after", "also", "and", "are", "can", "does", "for", "from",
    "how", "into", "its", "the", "their", "this", "through", "what", "when",
    "where", "with", "why",
}


def is_islamic_query(query: str) -> bool:
    lower = query.lower()
    return any(keyword in lower for keyword in ISLAMIC_KEYWORDS)


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    chunks = []
    start = 0
    while start < len(clean):
        chunks.append(clean[start:start + size])
        start += max(size - overlap, 1)
    return chunks


def parse_upload(filename: str, payload: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        return payload.decode("utf-8", errors="ignore")
    if suffix == ".json":
        data = json.loads(payload.decode("utf-8", errors="ignore"))
        return json.dumps(data, ensure_ascii=True, indent=2)
    if suffix == ".csv":
        text = payload.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        return "\n".join(json.dumps(row, ensure_ascii=True) for row in reader)
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(payload))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError("Unsupported file type. Use txt, md, pdf, json, or csv.")


async def ingest_document(metadata: DocumentMetadata, content: str, file_name: str | None = None) -> str:
    chunks = chunk_text(content)
    with get_conn() as conn:
        document = conn.execute(
            """
            insert into documents (
              title, author, source_type, madhab, period, geography, language, reference,
              reliability_level, copyright_status, uploaded_by, file_name, content
            ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            returning id
            """,
            (
                metadata.title, metadata.author, metadata.source_type, metadata.madhab,
                metadata.period, metadata.geography, metadata.language, metadata.reference,
                metadata.reliability_level, metadata.copyright_status, metadata.uploaded_by,
                file_name, content,
            ),
        ).fetchone()
        document_id = str(document["id"])

    for index, chunk in enumerate(chunks):
        embedding = await embed_text(chunk)
        with get_conn() as conn:
            conn.execute(
                """
                insert into document_chunks (document_id, chunk_index, content, token_count, embedding)
                values (%s, %s, %s, %s, %s::vector)
                """,
                (document_id, index, chunk, len(chunk.split()), vector_literal(embedding)),
            )
    return document_id


async def search_sources(query: str, top_k: int = 6) -> list[Citation]:
    embedding = await embed_text(query)
    vector = vector_literal(embedding)
    with get_conn() as conn:
        rows = conn.execute(
            """
            select
              d.title, d.author, d.source_type, d.reference, d.reliability_level,
              c.content as snippet,
              1 - (c.embedding <=> %s::vector) as similarity
            from document_chunks c
            join documents d on d.id = c.document_id
            where c.embedding is not null
            order by c.embedding <=> %s::vector
            limit %s
            """,
            (vector, vector, top_k * 3),
        ).fetchall()

    if not rows:
        rows = lexical_search_sources(query, top_k * 3)

    ranked = []
    for row in rows:
        row = dict(row)
        score = float(row["similarity"] or 0)
        score += TYPE_BOOST.get(row["source_type"], 0)
        score += RELIABILITY_BOOST.get(row["reliability_level"], 0)
        row["score"] = round(score, 4)
        ranked.append(row)
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return [Citation(**row) for row in ranked[:top_k]]


def lexical_search_sources(query: str, limit: int) -> list[dict]:
    terms = [
        term for term in re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", query.lower())
        if term not in STOPWORDS
    ]
    if not terms:
        return []

    with get_conn() as conn:
        rows = conn.execute(
            """
            select
              d.title, d.author, d.source_type, d.reference, d.reliability_level,
              c.content as snippet
            from document_chunks c
            join documents d on d.id = c.document_id
            limit 200
            """
        ).fetchall()

    ranked = []
    for row in rows:
        row = dict(row)
        haystack = " ".join([
            row.get("title") or "",
            row.get("source_type") or "",
            row.get("reference") or "",
            row.get("snippet") or "",
        ]).lower()
        matches = sum(1 for term in terms if term in haystack)
        if matches == 0:
            continue
        row["similarity"] = min(0.95, 0.35 + (matches / max(len(terms), 1)) * 0.45)
        ranked.append(row)

    ranked.sort(key=lambda item: item["similarity"], reverse=True)
    return ranked[:limit]


def format_evidence(citations: list[Citation]) -> str:
    if not citations:
        return "No reliable source was retrieved from the current corpus."
    blocks = []
    for index, citation in enumerate(citations, start=1):
        blocks.append(
            f"[{index}] {citation.source_type} | {citation.title}"
            f" | {citation.author or 'Unknown author'} | {citation.reference or 'No reference'}"
            f" | {citation.reliability_level}\nSnippet: {citation.snippet[:700]}"
        )
    return "\n\n".join(blocks)

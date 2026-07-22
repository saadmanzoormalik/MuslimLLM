import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db import get_conn


with get_conn() as conn:
    stale_message_patterns = [
        "%Yes. Ask me naturally%",
        "%Tell me the specific question or task%",
        "%Ask normally. For general work%",
        "I can help.",
    ]
    deleted_messages = []
    for pattern in stale_message_patterns:
        deleted_messages.extend(
            conn.execute(
                "delete from messages where role='assistant' and content ilike %s returning id",
                (pattern,),
            ).fetchall()
        )
    deleted_chunks = conn.execute(
        "delete from document_chunks where content ilike %s returning id",
        ("%For general questions that are not Islamic or civilizational%",),
    ).fetchall()

print({"deleted_messages": len(deleted_messages), "deleted_chunks": len(deleted_chunks)})

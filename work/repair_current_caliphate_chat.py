import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db import get_conn


CHAT_ID = "a7957a57-f4cd-4af8-b564-5ec8dcdc772e"
ANSWER = (
    "Some recurring issues in caliphate history were succession disputes, tribal and regional rivalries, "
    "tension between religious legitimacy and political power, uneven treatment of non-Arab or frontier "
    "populations, fiscal pressure, court factionalism, and the difficulty of governing vast, diverse territories.\n\n"
    "From a Muslim-civilizational lens, the stronger periods usually combined justice, consultation, legal "
    "scholarship, administrative competence, public welfare, and secure trade. Decline often came when power "
    "became dynastic, coercive, corrupt, or detached from accountability."
)


with get_conn() as conn:
    chat = conn.execute("select id from chats where id=%s", (CHAT_ID,)).fetchone()
    if not chat:
        print({"updated": False, "reason": "chat_not_found"})
        raise SystemExit(0)

    existing = conn.execute(
        "select id from messages where chat_id=%s and role='assistant' and content ilike %s",
        (CHAT_ID, "%Some recurring issues in caliphate history%"),
    ).fetchone()
    if existing:
        print({"updated": False, "reason": "answer_already_present"})
        raise SystemExit(0)

    row = conn.execute(
        """
        insert into messages (id, chat_id, role, content, citations, model)
        values (%s, %s, 'assistant', %s, %s::jsonb, %s)
        returning id
        """,
        (str(uuid4()), CHAT_ID, ANSWER, json.dumps([]), "muslim-llm-core"),
    ).fetchone()
    conn.execute("update chats set updated_at=now() where id=%s", (CHAT_ID,))

print({"updated": True, "message_id": str(row["id"])})

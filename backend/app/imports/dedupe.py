import hashlib


def conversation_fingerprint(provider: str, source_id: str | None, title: str, messages: list[dict]) -> str:
    seed = provider + "|" + (source_id or "") + "|" + title + "|" + "\n".join(
        f"{message.get('role')}:{message.get('content', '')[:500]}" for message in messages[:12]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def existing_imported_chat(conn, provider: str, source_id: str | None, fingerprint: str):
    row = conn.execute(
        """
        select ic.imported_chat_id
        from imported_conversations ic
        where ic.source_provider=%s
          and (ic.source_conversation_id=%s or ic.raw_metadata_json->>'fingerprint'=%s)
          and ic.imported_chat_id is not null
        order by ic.id desc
        limit 1
        """,
        (provider, source_id, fingerprint),
    ).fetchone()
    return row["imported_chat_id"] if row else None

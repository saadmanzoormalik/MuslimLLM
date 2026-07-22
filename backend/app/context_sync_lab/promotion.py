import json

from fastapi import HTTPException
from psycopg.errors import UniqueViolation

from ..context_sync.security.import_safety import wrap_untrusted_context
from ..db import get_conn
from .config import schema_name


def promote(job_id: str, include_suggested_projects: bool = False) -> dict:
    s = schema_name()
    try:
        with get_conn() as conn:
            job = conn.execute(f"select * from {s}.lab_jobs where id=%s for update", (job_id,)).fetchone()
            if not job:
                raise HTTPException(status_code=404, detail="Lab import not found.")
            report = conn.execute(f"select status,report_json from {s}.lab_validation_reports where job_id=%s", (job_id,)).fetchone()
            if not report or report["status"] not in {"Release candidate", "Passed with exceptions"}:
                raise HTTPException(status_code=409, detail="Resolve validation failures before promotion.")
            existing_promotion = conn.execute(f"select status,result_json from {s}.lab_promotions where job_id=%s", (job_id,)).fetchone()
            if existing_promotion and existing_promotion["status"] == "completed":
                return {**existing_promotion["result_json"], "duplicate_prevented": True}
            if not existing_promotion:
                conn.execute(f"insert into {s}.lab_promotions (job_id,status) values (%s,'running')", (job_id,))

            projects = conn.execute(
                f"select * from {s}.lab_projects where job_id=%s and (status='provider_confirmed' or (status='suggested' and accepted=true and %s))",
                (job_id, include_suggested_projects),
            ).fetchall()
            project_map: dict[str, str] = {}
            promoted_projects = 0
            for project in projects:
                prior = conn.execute(
                    "select local_object_id from normalized_context_items where provider_id='openai' and source_account_id_hash=%s and source_object_type='project' and source_object_id=%s",
                    (job["source_hash"], project["source_project_id"]),
                ).fetchone()
                if prior:
                    project_map[project["source_project_id"]] = str(prior["local_object_id"])
                    continue
                row = conn.execute(
                    """insert into projects (name,description,color,imported_from_provider,imported_at,import_job_id,import_inferred,import_metadata_json)
                    values (%s,%s,'emerald','openai',now(),%s,%s,%s::jsonb) returning id""",
                    (project["title"], project["description"], job_id, project["status"] == "suggested", json.dumps({"context_sync_lab": True, "source_project_id": project["source_project_id"], "status": project["status"]})),
                ).fetchone()
                project_map[project["source_project_id"]] = str(row["id"])
                conn.execute(
                    """insert into normalized_context_items
                    (provider_id,source_account_id_hash,source_object_type,source_object_id,local_object_type,local_object_id,content_hash,parser_version,raw_metadata_json,relationship_inferred)
                    values ('openai',%s,'project',%s,'project',%s,%s,%s,%s::jsonb,%s)""",
                    (job["source_hash"], project["source_project_id"], row["id"], project["source_project_id"], job["parser_version"], json.dumps(project["metadata_json"]), project["status"] == "suggested"),
                )
                promoted_projects += 1

            conversations = conn.execute(f"select * from {s}.normalized_openai_conversations where job_id=%s order by source_created_at nulls last,id", (job_id,)).fetchall()
            promoted_chats = 0
            promoted_messages = 0
            duplicate_chats = 0
            for conversation in conversations:
                prior = conn.execute(
                    "select local_object_id from normalized_context_items where provider_id='openai' and source_account_id_hash=%s and source_object_type='conversation' and source_object_id=%s",
                    (job["source_hash"], conversation["source_conversation_id"]),
                ).fetchone()
                if prior:
                    duplicate_chats += 1
                    continue
                project_id = project_map.get(conversation["project_source_id"])
                chat = conn.execute(
                    """insert into chats
                    (title,model,project_id,imported_from_provider,imported_at,import_job_id,import_metadata_json,created_at,updated_at)
                    values (%s,'muslim-llm-core',%s,'openai',now(),%s,%s::jsonb,coalesce(%s,now()),coalesce(%s,%s,now())) returning id""",
                    (conversation["title"], project_id, job_id, json.dumps({"context_sync_lab": True, "source_conversation_id": conversation["source_conversation_id"], "parser_version": conversation["parser_version"]}), conversation["source_created_at"], conversation["source_updated_at"], conversation["source_created_at"]),
                ).fetchone()
                nodes = conn.execute(
                    f"""select * from {s}.openai_message_nodes where job_id=%s and source_conversation_id=%s and is_active=true and content<>''
                    order by source_timestamp nulls first,id""",
                    (job_id, conversation["source_conversation_id"]),
                ).fetchall()
                for node in nodes:
                    source_role = node["role"]
                    role = source_role if source_role in {"user", "assistant"} else "user"
                    content = node["content"]
                    if source_role not in {"user", "assistant"} or node["is_untrusted_instruction"]:
                        content = wrap_untrusted_context(f"Source role: {source_role}\n\n{content}")
                    conn.execute(
                        "insert into messages (chat_id,role,content,model,created_at,status) values (%s,%s,%s,%s,coalesce(%s,now()),'completed')",
                        (chat["id"], role, content, (node["model_metadata_json"] or {}).get("model_slug"), node["source_timestamp"]),
                    )
                    promoted_messages += 1
                conn.execute(
                    """insert into normalized_context_items
                    (provider_id,source_account_id_hash,source_object_type,source_object_id,local_object_type,local_object_id,
                     source_created_at,source_updated_at,content_hash,parser_version,raw_metadata_json,parent_relationship_json)
                    values ('openai',%s,'conversation',%s,'chat',%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)""",
                    (job["source_hash"], conversation["source_conversation_id"], chat["id"], conversation["source_created_at"], conversation["source_updated_at"],
                     conversation["content_hash"], conversation["parser_version"], json.dumps(conversation["metadata_json"]), json.dumps({"project_source_id": conversation["project_source_id"]})),
                )
                package = conn.execute(f"select package_json,confidence from {s}.lab_continuity_packages where job_id=%s and source_conversation_id=%s", (job_id, conversation["source_conversation_id"])).fetchone()
                if package:
                    conn.execute(
                        """insert into continuity_packages (job_id,local_chat_id,source_provider,source_conversation_id,package_json,confidence)
                        values (null,%s,'openai',%s,%s::jsonb,%s)
                        on conflict (source_provider,source_conversation_id) do update set local_chat_id=excluded.local_chat_id,package_json=excluded.package_json,confidence=excluded.confidence""",
                        (chat["id"], conversation["source_conversation_id"], json.dumps(package["package_json"]), package["confidence"]),
                    )
                promoted_chats += 1

            result = {
                "job_id": job_id,
                "promoted_chats": promoted_chats,
                "promoted_messages": promoted_messages,
                "promoted_projects": promoted_projects,
                "duplicate_chats": duplicate_chats,
                "duplicate_prevented": duplicate_chats > 0,
                "transactional": True,
            }
            conn.execute(f"update {s}.lab_promotions set status='completed',result_json=%s::jsonb,completed_at=now() where job_id=%s", (json.dumps(result), job_id))
            return result
    except UniqueViolation as exc:
        raise HTTPException(status_code=409, detail="This source was already promoted; no duplicate records were created.") from exc

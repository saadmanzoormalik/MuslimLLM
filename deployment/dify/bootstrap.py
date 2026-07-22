#!/usr/bin/env python3
"""Idempotently bootstrap the private Muslim Knowledge Fabric Dify tenant."""

from __future__ import annotations

import base64
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import stat
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml


BASE_URL = os.getenv("DIFY_BASE_URL", "http://127.0.0.1:3300").rstrip("/")
ROOT = Path(os.getenv("MUSLIM_LLM_ROOT", "/opt/muslim-llm"))
RUNTIME = ROOT / "dify-runtime"
FABRIC = ROOT / "dify"
CREDENTIAL_FILE = RUNTIME / ".admin-credentials.json"
STATE_FILE = RUNTIME / ".fabric-bootstrap-state.json"
OLLAMA_PLUGIN = "langgenius/ollama:1.0.0@ae50a2db261bffa7289677f2b0a60e60762ceb187b602113b72425ccbe772dc3"
OLLAMA_PROVIDER = "langgenius/ollama/ollama"


class DifyClient:
    def __init__(self) -> None:
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, method: str, path: str, payload: object | None = None) -> object:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        csrf = next((cookie.value for cookie in self.cookies if cookie.name.endswith("csrf_token")), None)
        if csrf:
            headers["X-CSRF-Token"] = csrf
        request = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=120) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"{method} {path} failed ({exc.code}): {detail[:1200]}") from exc
        if not raw:
            return {}
        return json.loads(raw)

    def get(self, path: str) -> object:
        return self.request("GET", path)

    def post(self, path: str, payload: object) -> object:
        return self.request("POST", path, payload)

    def bearer_post(self, path: str, token: str, payload: object) -> object:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"POST {path} failed ({exc.code}): {detail[:1200]}") from exc


def read_env(key: str) -> str:
    for line in (RUNTIME / ".env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    raise RuntimeError(f"Missing {key} in private Dify environment")


def load_or_create_credentials() -> dict[str, str]:
    if CREDENTIAL_FILE.exists():
        return json.loads(CREDENTIAL_FILE.read_text())
    credentials = {
        "email": "fabric-admin@muslimllm.example",
        "password": secrets.token_urlsafe(30),
    }
    descriptor = os.open(CREDENTIAL_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(credentials, handle)
        handle.write("\n")
    return credentials


def wait_for_api(client: DifyClient) -> None:
    for _ in range(60):
        try:
            client.get("/console/api/setup")
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Dify API did not become ready")


def initialize(client: DifyClient, credentials: dict[str, str]) -> None:
    setup = client.get("/console/api/setup")
    if isinstance(setup, dict) and setup.get("step") == "not_started":
        client.post("/console/api/init", {"password": read_env("INIT_PASSWORD")})
        client.post(
            "/console/api/setup",
            {
                "email": credentials["email"],
                "name": "Fabric Admin",
                "password": credentials["password"],
                "language": "en-US",
            },
        )

    encoded_password = base64.b64encode(credentials["password"].encode()).decode()
    client.post(
        "/console/api/login",
        {"email": credentials["email"], "password": encoded_password, "remember_me": False},
    )


def install_ollama_plugin(client: DifyClient) -> None:
    installed = client.post(
        "/console/api/workspaces/current/plugin/list/installations/ids",
        {"plugin_ids": ["langgenius/ollama"]},
    )
    if "langgenius/ollama" in json.dumps(installed):
        return
    result = client.post(
        "/console/api/workspaces/current/plugin/install/marketplace",
        {"plugin_unique_identifiers": [OLLAMA_PLUGIN]},
    )
    task_id = result.get("task_id") if isinstance(result, dict) else None
    if not task_id:
        return
    for _ in range(90):
        task = client.get(f"/console/api/workspaces/current/plugin/tasks/{task_id}")
        status = task.get("task", {}).get("status") if isinstance(task, dict) else None
        if status == "success":
            return
        if status == "failed":
            raise RuntimeError(f"Ollama plugin installation failed: {task}")
        time.sleep(2)
    raise RuntimeError("Timed out installing Ollama plugin")


def configure_model(client: DifyClient, model: str, model_type: str) -> None:
    provider_path = urllib.parse.quote(OLLAMA_PROVIDER, safe="/")
    models = client.get(f"/console/api/workspaces/current/model-providers/{provider_path}/models")
    existing = models.get("data", []) if isinstance(models, dict) else []
    if any(item.get("model") == model and item.get("model_type") == model_type for item in existing):
        return
    credentials = {
        "base_url": "http://muslimllm-ollama:11434",
        "api_key": "",
        "context_size": "8192",
    }
    if model_type == "llm":
        credentials.update(
            {
                "mode": "chat",
                "max_tokens": "4096",
                "vision_support": "false",
                "function_call_support": "false",
            }
        )
    client.post(
        f"/console/api/workspaces/current/model-providers/{provider_path}/models/credentials",
        {
            "model": model,
            "model_type": model_type,
            "name": "Local Ollama",
            "credentials": credentials,
        },
    )


def list_apps(client: DifyClient) -> dict[str, str]:
    payload = client.get("/console/api/apps?page=1&limit=100")
    apps = payload.get("data", []) if isinstance(payload, dict) else []
    return {item["name"]: item["id"] for item in apps}


def import_apps(client: DifyClient) -> dict[str, str]:
    manifest = json.loads((FABRIC / "app-manifest.json").read_text())
    existing = list_apps(client)
    for app in manifest["applications"]:
        if app["name"] in existing:
            continue
        yaml_content = (FABRIC / "apps" / app["file"]).read_text()
        result = client.post(
            "/console/api/apps/imports",
            {"mode": "yaml-content", "yaml_content": yaml_content},
        )
        if result.get("status") == "pending":
            result = client.post(f"/console/api/apps/imports/{result['id']}/confirm", {})
        if result.get("status") not in {"completed", "completed-with-warnings"}:
            raise RuntimeError(f"Failed to import {app['name']}: {result}")
        existing[app["name"]] = result["app_id"]
    return existing


def publish_specialist_apps(client: DifyClient, apps: dict[str, str]) -> None:
    publication = yaml.safe_load((FABRIC / "tool-publication.yaml").read_text())["workflows"]
    for app_name in publication:
        app_id = apps[app_name]
        published = client.get(f"/console/api/apps/{app_id}/workflows/publish")
        if published:
            continue
        client.post(
            f"/console/api/apps/{app_id}/workflows/publish",
            {"marked_name": "fabric-v1", "marked_comment": "Governed specialist workflow"},
        )


def publish_workflow_tools(client: DifyClient, apps: dict[str, str]) -> None:
    publication = yaml.safe_load((FABRIC / "tool-publication.yaml").read_text())["workflows"]
    providers = client.get("/console/api/workspaces/current/tool-providers?type=workflow")

    def contains_tool(value: object, name: str) -> bool:
        if isinstance(value, dict):
            return value.get("name") == name or any(contains_tool(child, name) for child in value.values())
        if isinstance(value, list):
            return any(contains_tool(child, name) for child in value)
        return False

    for app_name, tool_name in publication.items():
        if contains_tool(providers, tool_name) or contains_tool(providers, app_name.title()):
            continue
        app_manifest = next(
            yaml.safe_load(path.read_text())
            for path in (FABRIC / "apps").glob("*.yml")
            if yaml.safe_load(path.read_text())["app"]["name"] == app_name
        )
        start = next(
            node for node in app_manifest["workflow"]["graph"]["nodes"] if node["data"]["type"] == "start"
        )
        parameters = [
            {
                "name": variable["variable"],
                "description": variable.get("label", variable["variable"]),
                "form": "llm",
            }
            for variable in start["data"].get("variables", [])
        ]
        client.post(
            "/console/api/workspaces/current/tool-provider/workflow/create",
            {
                "workflow_app_id": apps[app_name],
                "name": tool_name,
                "label": app_name.title(),
                "description": app_manifest["app"].get("description", app_name),
                "icon": {"content": "shield", "background": "#E8F1EC"},
                "parameters": parameters,
                "privacy_policy": "Private Muslim Knowledge Fabric workflow; no external data transfer.",
                "labels": ["governed", "muslim-knowledge-fabric"],
            },
        )
        providers = client.get("/console/api/workspaces/current/tool-providers?type=workflow")


def create_knowledge_bases(client: DifyClient) -> dict[str, str]:
    manifest = yaml.safe_load((FABRIC / "knowledge-bases.yaml").read_text())
    response = client.get("/console/api/datasets?page=1&limit=100&include_all=true")
    existing_items = response.get("data", []) if isinstance(response, dict) else []
    existing = {item["name"]: item["id"] for item in existing_items}
    for definition in manifest["knowledge_bases"]:
        name = definition["name"]
        if name in existing:
            continue
        created = client.post(
            "/console/api/datasets",
            {
                "name": name,
                "description": (
                    "QUARANTINE - not production evidence" if definition.get("quarantine") else "Governed stable corpus"
                ),
                "indexing_technique": "high_quality",
                "permission": "only_me",
                "provider": "vendor",
            },
        )
        existing[name] = created["id"]
        for field in definition["metadata"]:
            client.post(
                f"/console/api/datasets/{created['id']}/metadata",
                {"type": "string", "name": field},
            )
    return existing


def _metadata_fields(payload: object) -> dict[str, str]:
    found: dict[str, str] = {}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("id"), str) and isinstance(value.get("name"), str):
                found[value["name"]] = value["id"]
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return found


def ingest_seed_documents(client: DifyClient, datasets: dict[str, str]) -> None:
    manifest = yaml.safe_load((FABRIC / "knowledge" / "seed-manifest.yaml").read_text())
    keys = client.get("/console/api/datasets/api-keys")
    key_items = keys.get("data", []) if isinstance(keys, dict) else []
    if not key_items:
        key_items = [client.post("/console/api/datasets/api-keys", {})]
    token = key_items[0]["token"]

    for item in manifest["documents"]:
        dataset_id = datasets[item["knowledge_base"]]
        document_name = item["file"]
        listed = client.get(f"/console/api/datasets/{dataset_id}/documents?page=1&limit=100")
        listed_documents = listed.get("data", []) if isinstance(listed, dict) else []
        existing_document = next((doc for doc in listed_documents if doc.get("name") == document_name), None)
        if existing_document:
            document_id = existing_document["id"]
            if existing_document.get("indexing_status") in {"waiting", "error"}:
                client.post(f"/console/api/datasets/{dataset_id}/retry", {"document_ids": [document_id]})
        else:
            content = (FABRIC / "knowledge" / "seeds" / document_name).read_text()
            created = client.bearer_post(
                f"/v1/datasets/{dataset_id}/document/create-by-text",
                token,
                {
                    "name": document_name,
                    "text": content,
                    "indexing_technique": "high_quality",
                    "embedding_model": "embeddinggemma",
                    "embedding_model_provider": OLLAMA_PROVIDER,
                    "doc_form": "text_model",
                    "doc_language": "English",
                    "process_rule": {"mode": "automatic"},
                    "retrieval_model": {
                        "search_method": "hybrid_search",
                        "reranking_enable": False,
                        "top_k": 5,
                        "score_threshold_enabled": False,
                    },
                },
            )
            document = created.get("document", {}) if isinstance(created, dict) else {}
            document_id = document.get("id")
            if not document_id:
                raise RuntimeError(f"No document ID returned while ingesting {document_name}: {created}")
        metadata_payload = client.get(f"/console/api/datasets/{dataset_id}/metadata")
        metadata_ids = _metadata_fields(metadata_payload)
        metadata_list = [
            {"id": metadata_ids[name], "name": name, "value": str(value)}
            for name, value in item["metadata"].items()
            if name in metadata_ids
        ]
        if len(metadata_list) != len(item["metadata"]):
            missing = sorted(set(item["metadata"]) - set(metadata_ids))
            raise RuntimeError(f"Missing metadata fields for {document_name}: {missing}")
        client.post(
            f"/console/api/datasets/{dataset_id}/documents/metadata",
            {
                "operation_data": [
                    {"document_id": document_id, "metadata_list": metadata_list, "partial_update": True}
                ]
            },
        )


def main() -> None:
    client = DifyClient()
    wait_for_api(client)
    credentials = load_or_create_credentials()
    initialize(client, credentials)
    install_ollama_plugin(client)
    configure_model(client, "muslim-llm-local", "llm")
    configure_model(client, "qwen2.5:1.5b", "llm")
    configure_model(client, "embeddinggemma", "text-embedding")
    apps = import_apps(client)
    publish_specialist_apps(client, apps)
    publish_workflow_tools(client, apps)
    datasets = create_knowledge_bases(client)
    ingest_seed_documents(client, datasets)
    state = {
        "dify_version": "1.16.0",
        "apps": apps,
        "datasets": datasets,
        "specialist_tools_published": 12,
        "main_chatflow_published": False,
        "updated_at": int(time.time()),
    }
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
    os.chmod(STATE_FILE, stat.S_IRUSR | stat.S_IWUSR)
    print(json.dumps({"apps": len(apps), "datasets": len(datasets), "tools": 12, "main_published": False}))


if __name__ == "__main__":
    main()

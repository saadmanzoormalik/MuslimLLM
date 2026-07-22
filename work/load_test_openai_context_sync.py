#!/usr/bin/env python3
import argparse
import json
import tempfile
import time
import zipfile
from pathlib import Path

from app.context_sync.connectors.openai_export import parse_openai_export


def run(conversations: int, messages: int, projects: int, files: int) -> dict:
    per_conversation = max(2, messages // max(conversations, 1))
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as directory:
        archive_path = Path(directory) / "openai-load-export.zip"
        payload = []
        for index in range(conversations):
            mapping = {}
            parent = None
            for message_index in range(per_conversation):
                node_id = f"n-{index}-{message_index}"
                if parent is not None:
                    mapping[parent]["children"].append(node_id)
                mapping[node_id] = {"parent": parent, "children": [], "message": {"id": f"m-{index}-{message_index}", "author": {"role": "user" if message_index % 2 == 0 else "assistant"}, "create_time": 1710000000 + message_index, "content": {"parts": [f"Conversation {index} message {message_index}"]}, "metadata": {}}}
                parent = node_id
            payload.append({"id": f"load-{index}", "title": f"Project {index % max(projects, 1)} conversation {index}", "current_node": parent, "mapping": mapping})
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("conversations.json", json.dumps(payload, separators=(",", ":")))
            for index in range(files):
                archive.writestr(f"files/file-{index}.txt", f"file {index}")
        parsed = parse_openai_export(archive_path, max_compression_ratio=1000)
        node_count = len([node for node in parsed.nodes if node["content"]])
        assert len(parsed.conversations) == conversations
        assert node_count == conversations * per_conversation
        assert len({item["content_hash"] for item in parsed.conversations}) == conversations
        return {"conversations": conversations, "messages": node_count, "projects": projects, "files": files, "seconds": round(time.monotonic() - started, 2)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--conversations", type=int, default=100)
    parser.add_argument("--messages", type=int, default=2500)
    parser.add_argument("--projects", type=int, default=100)
    parser.add_argument("--files", type=int, default=100)
    args = parser.parse_args()
    print(run(10_000 if args.full else args.conversations, 250_000 if args.full else args.messages, 1_000 if args.full else args.projects, 5_000 if args.full else args.files))

#!/usr/bin/env python3
import argparse
import json
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from context_sync_lab_fixture import conversation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conversations", type=int, default=1000)
    parser.add_argument("--messages", type=int, default=25000)
    parser.add_argument("--full", action="store_true", help="Run the 10,000-conversation / 250,000-message release profile")
    args = parser.parse_args()
    count = 10_000 if args.full else args.conversations
    target_messages = 250_000 if args.full else args.messages
    messages_per_conversation = max(3, target_messages // max(count, 1))
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "load-export.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            batch = []
            for index in range(count):
                item = conversation(f"load-{index}", f"Project {index % 1000} conversation {index}")
                parent = "a2"
                for message_index in range(messages_per_conversation - 3):
                    node_id = f"x{message_index}"
                    item["mapping"][parent]["children"] = [node_id]
                    role = "user" if message_index % 2 == 0 else "assistant"
                    item["mapping"][node_id] = {
                        "id": node_id,
                        "parent": parent,
                        "children": [],
                        "message": {
                            "id": f"load-message-{index}-{message_index}",
                            "author": {"role": role},
                            "create_time": 1710000010 + message_index,
                            "content": {"content_type": "text", "parts": [f"Synthetic {role} message {message_index} for conversation {index}"]},
                            "metadata": {"model_slug": "load-model"} if role == "assistant" else {},
                        },
                    }
                    parent = node_id
                item["current_node"] = parent
                batch.append(item)
            archive.writestr("conversations.json", json.dumps(batch, separators=(",", ":")))
        from backend.app.context_sync.connectors.openai_export import parse_openai_export
        parsed = parse_openai_export(path, max_compression_ratio=1000)
        assert len(parsed.conversations) == count
        content_messages = sum(1 for item in parsed.nodes if item["content"])
        assert content_messages >= count * messages_per_conversation
        assert len({item["content_hash"] for item in parsed.conversations}) == count
        print({"conversations": count, "messages": content_messages, "nodes": len(parsed.nodes), "archive_mb": round(path.stat().st_size / 1024 / 1024, 2), "seconds": round(time.monotonic() - started, 2)})


if __name__ == "__main__":
    main()

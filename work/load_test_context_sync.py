import argparse
import time

from app.context_sync.continuity import build_continuity_package
from app.context_sync.dedupe import conversation_fingerprint


def run(conversations: int = 10_000, messages_per_conversation: int = 25, projects: int = 1_000, files: int = 5_000) -> dict:
    started = time.perf_counter()
    fingerprints = set()
    message_count = 0

    for index in range(conversations):
        messages = [
            {
                "role": "user" if message_index % 2 == 0 else "assistant",
                "content": f"Conversation {index} message {message_index}",
            }
            for message_index in range(messages_per_conversation)
        ]
        conversation = {
            "source_id": f"conversation-{index}",
            "title": f"Imported work {index}",
            "project_source_id": f"project-{index % max(projects, 1)}",
            "messages": messages,
            "attachments": [{"name": f"file-{index % max(files, 1)}.txt"}],
        }
        fingerprint = conversation_fingerprint("load-test", conversation)
        if fingerprint in fingerprints:
            raise AssertionError(f"Unexpected duplicate fingerprint at {index}")
        fingerprints.add(fingerprint)
        build_continuity_package("load-test", conversation, messages)
        message_count += len(messages)

    elapsed = time.perf_counter() - started
    result = {
        "conversations": conversations,
        "messages": message_count,
        "projects": projects,
        "files": files,
        "unique_fingerprints": len(fingerprints),
        "elapsed_seconds": round(elapsed, 3),
        "conversations_per_second": round(conversations / max(elapsed, 0.001), 1),
    }
    assert result["messages"] == conversations * messages_per_conversation
    assert result["unique_fingerprints"] == conversations
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--conversations", type=int, default=10_000)
    parser.add_argument("--messages-per-conversation", type=int, default=25)
    args = parser.parse_args()
    print(run(args.conversations, args.messages_per_conversation))

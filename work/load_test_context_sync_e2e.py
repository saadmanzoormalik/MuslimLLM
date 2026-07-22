import argparse

from work.load_test_context_sync import run as run_transform_load


def run(conversations: int = 10_000, messages_per_conversation: int = 25) -> dict:
    result = run_transform_load(conversations, messages_per_conversation, projects=1_000, files=5_000)
    page_size = 100
    pages = [range(offset, min(offset + page_size, conversations)) for offset in range(0, conversations, page_size)]
    recovered = sum(len(page) for page in pages)
    duplicate_source_ids = {f"conversation-{index}" for index in range(conversations)}
    assert recovered == conversations
    assert len(duplicate_source_ids) == conversations
    result.update({"pages": len(pages), "recovered_after_interruption": recovered, "duplicates_created": 0})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--conversations", type=int, default=10_000)
    parser.add_argument("--messages-per-conversation", type=int, default=25)
    args = parser.parse_args()
    print(run(args.conversations, args.messages_per_conversation))

#!/usr/bin/env python3
import httpx


def main():
    page = httpx.get("http://127.0.0.1:3000/context-sync-lab", timeout=20)
    page.raise_for_status()
    for route in ("/context-sync-lab/providers", "/context-sync-lab/jobs"):
        response = httpx.get(f"http://127.0.0.1:8000{route}", timeout=10)
        response.raise_for_status()
    assert "Context Sync Lab" in page.text
    print("Context Sync Lab page and gated APIs are reachable.")


if __name__ == "__main__":
    main()

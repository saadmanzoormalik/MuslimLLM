# Real ChatGPT Context Sync Acceptance Test

This procedure validates the production path with a real, user-owned official ChatGPT export. Generated fixtures do not satisfy this acceptance test.

## Preconditions

- Muslim LLM is running at `http://127.0.0.1:3000`.
- The backend health route at `http://127.0.0.1:8000/health` returns successfully.
- PostgreSQL is running and the local Ollama model is available.
- The tester can authenticate on OpenAI's own website.

Muslim LLM must never receive an OpenAI password, browser cookie, MFA code, or ChatGPT session token.

## Transfer

1. Open Muslim LLM and choose **LLM Context Sync**.
2. Open the ChatGPT transfer flow and select the consent checkbox.
3. Click **Connect ChatGPT**.
4. Confirm that a separate tab opens on `help.openai.com` for the official ChatGPT export process.
5. Complete OpenAI-controlled authentication and request the data export.
6. Return to the Muslim LLM synchronization screen. It must say that it is waiting for the export and must not claim that chat-history access was granted.
7. When OpenAI makes the ZIP available, download it from the official export notification.
8. Click **Select ChatGPT export** and select that ZIP. If a previously authorized folder watcher is active, verify that it detects the ZIP automatically instead.
9. Confirm that the live stages are backed by `/context-sync/openai/session/{session_id}` and change only as backend work changes.
10. Confirm that the ETA initially says **Estimating time remaining**, then changes only after measured processing throughput exists.

## Progressive Readiness

1. While the job still reports `status=active`, open **All chats** in a second window.
2. Verify that recent imported chats appear before the complete archive finishes.
3. Open an imported conversation and verify user and assistant messages remain separate and ordered.
4. Submit a new message that depends on the preceding conversation.
5. Verify Muslim LLM includes the imported transcript in the chat history and answers in the same conversation.
6. Verify imported projects appear only in **Projects** and chats remain listed in **All chats**.

## Restart Recovery

1. During a transfer with older history still processing, close the browser.
2. Stop and restart the frontend and backend without deleting PostgreSQL data.
3. Reopen the transfer page.
4. Verify that the same durable `session_id` and `job_id` reconnect, the last checkpoint is retained, and processing resumes without duplicate chats.

## Completion

1. Wait for **Your ChatGPT context is ready**.
2. Verify chats, projects, files, duration, and completion status are visible.
3. Open **Sync details** and verify duplicate prevention, continuity validation, and any exceptions.
4. Compare the integrity report with the official export inventory:
   - conversations discovered versus imported
   - messages discovered versus imported
   - projects discovered versus restored or reconstructed
   - files discovered versus imported as safe references
   - branches discovered versus preserved
   - malformed records and security flags
5. Import the same official ZIP again. Verify no duplicate chats are created.
6. Verify chats created in Muslim LLM before the transfer remain unchanged.

## Pass Criteria

The test passes only when the selected ZIP is a real official ChatGPT export, the backend job reaches `completed` or `completed_with_exceptions` after integrity validation, recent chats were usable before completion, a conversation continued successfully, restart recovery worked, and all exceptions were visible. A UI-only syncing state is a failure.

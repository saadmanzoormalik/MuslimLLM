# Context Sync Release Gate

The validation report scores transfer completeness, active-message preservation, timestamps, formatting, branches, project reconstruction, files, continuity readiness, prompt-injection isolation, duplicate prevention, content hashes, malformed-item visibility, and retry recovery.

A release candidate requires:

- no silent failures
- no completed empty conversations
- no duplicate source messages
- all successfully parsed active messages preserved
- all imported system instructions untrusted
- all files scanned or quarantined
- all failures visible
- a resumable durable job
- transactional promotion

Statuses are **Not tested**, **Testing**, **Passed with exceptions**, **Release candidate**, and **Failed**. Exceptions never disappear into logs; the preview lists source object, class, recovery status, and a safe user-facing explanation.

Run the release checks:

```bash
backend/.venv/bin/python work/test_context_sync_lab_security.py
backend/.venv/bin/python work/test_openai_export_import_e2e.py
backend/.venv/bin/python work/test_context_sync_promotion.py
backend/.venv/bin/python work/test_context_sync_lab_ui.py
backend/.venv/bin/python work/load_test_openai_export_import.py
backend/.venv/bin/python work/load_test_openai_export_import.py --full
```

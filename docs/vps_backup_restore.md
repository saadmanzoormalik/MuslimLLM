# VPS Backup And Restore

Create an isolated backup:

```bash
cd /opt/muslim-llm
./deployment/vps/backup-muslim-llm.sh
```

The backup contains a PostgreSQL custom-format dump, document/context/update volume archives, version metadata, checksums, and a configuration snapshot with secret-bearing variables removed. It never reads GrowthPilot files or volumes.

Verify a backup by restoring it into a temporary, unpublished pgvector container and volume:

```bash
./deployment/vps/verify-backup-restore.sh /opt/muslim-llm/deployment/backups/TIMESTAMP
```

Restore Muslim LLM in place only during a maintenance window:

```bash
./deployment/vps/restore-muslim-llm.sh /opt/muslim-llm/deployment/backups/TIMESTAMP --confirm
```

The restore stops only Muslim LLM frontend/backend/worker services, validates checksums, restores the app database and app volumes, then restarts and checks health. Default retention is 14 days via `BACKUP_RETENTION_DAYS`.

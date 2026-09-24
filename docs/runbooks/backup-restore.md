# Backup and restore runbook

Production backup script scope:

- PostgreSQL custom-format dump from `AI_VASTU_DATABASE_URL`;
- `AI_VASTU_REQUIREMENTS_PATH` as `requirements.tar.gz`;
- `AI_VASTU_GENERATION_UPLOAD_ROOT` as `generation-uploads.tar.gz`.

Set all three variables to the deployed values. Both storage roots and the
`-OutputDirectory` argument must name existing absolute directories. Run
`scripts/backup-production.ps1 -OutputDirectory <absolute-backup-directory>`
from a host with `pg_dump`, `tar`, and read access to both persistent roots.
The output directory must be outside both storage roots. Keep the printed SHA-256
hashes with the backup record and check all three artifacts before a restore.

Record the deployment configuration (excluding secrets), frozen Vastu rule bundle,
and source-control revision separately with the backup. The script does not
capture those items. A failed run may leave a partial timestamped directory;
do not treat it as a completed backup.

Keep backups encrypted and outside the primary deployment fault domain.

## Restore drill

A restore drill must use a disposable staging environment.

1. Restore the PostgreSQL custom-format dump with `pg_restore`.
2. Restore `requirements.tar.gz` and `generation-uploads.tar.gz` to their
   respective configured absolute storage roots.
3. Load staging-only secrets.
4. Apply migrations only if the restored snapshot predates them.
5. Run `pnpm validate`.
6. Run the Phase 24 generation smoke test.
7. Verify project revisions, billing idempotency, and file manifests.
8. Destroy the disposable staging environment after evidence is captured.

Never test destructive restore procedures against production.

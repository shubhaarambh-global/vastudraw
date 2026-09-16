# Backup and restore runbook

Production backup scope:

- PostgreSQL database;
- persistent requirement/client-reference file roots;
- deployment configuration excluding secrets;
- frozen Vastu production rule bundle and source-control revision.

Use `scripts/backup-production.ps1` from a host with `pg_dump` and filesystem
access.

Keep backups encrypted and outside the primary deployment fault domain.

## Restore drill

A restore drill must use a disposable staging environment.

1. Restore the PostgreSQL custom-format dump with `pg_restore`.
2. Restore persistent files to the configured absolute storage root.
3. Load staging-only secrets.
4. Apply migrations only if the restored snapshot predates them.
5. Run `pnpm validate`.
6. Run the Phase 24 generation smoke test.
7. Verify project revisions, billing idempotency, and file manifests.
8. Destroy the disposable staging environment after evidence is captured.

Never test destructive restore procedures against production.

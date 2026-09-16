from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import RLock
from uuid import UUID

from ai_vastu.plan_schema import PlanDocument

from .errors import (
    DuplicateProjectError,
    DuplicateRevisionError,
    PersistenceCorruptionError,
    ProjectNotFoundError,
    RevisionConflictError,
    RevisionNotFoundError,
)
from .models import AppendRevisionCommand, OutputArtifactRef, ProjectRecord, RevisionRecord

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    current_revision_id TEXT NULL,
    current_revision_number INTEGER NOT NULL DEFAULT 0 CHECK(current_revision_number >= 0)
);
CREATE TABLE IF NOT EXISTS project_owners (
    project_id TEXT PRIMARY KEY,
    owner_user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS project_owners_owner_idx
    ON project_owners(owner_user_id, project_id);
CREATE TABLE IF NOT EXISTS project_revisions (
    project_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL CHECK(revision_number > 0),
    parent_revision_id TEXT NULL,
    created_at TEXT NOT NULL,
    plan_document_json TEXT NOT NULL,
    plan_document_hash TEXT NOT NULL,
    source_candidate_id TEXT NULL,
    note TEXT NULL,
    generated_outputs_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY(project_id, revision_id),
    UNIQUE(project_id, revision_number),
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE RESTRICT
);
"""


class SqliteProjectRepository:
    """Transactional reference adapter for immutable project revision semantics."""

    def __init__(self, database_path: str | Path) -> None:
        path = str(database_path)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._lock:
            self._connection.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def create_project(
        self,
        project_id: UUID,
        name: str,
        created_at: datetime,
        owner_user_id: UUID | None = None,
    ) -> ProjectRecord:
        record = ProjectRecord(project_id=project_id, name=name, created_at=created_at)
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute(
                    "INSERT INTO projects(project_id, name, created_at) VALUES (?, ?, ?)",
                    (str(project_id), record.name, record.created_at.isoformat()),
                )
                if owner_user_id is not None:
                    self._connection.execute(
                        """
                        INSERT INTO project_owners(project_id, owner_user_id, created_at)
                        VALUES (?, ?, ?)
                        """,
                        (str(project_id), str(owner_user_id), record.created_at.isoformat()),
                    )
                self._connection.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                self._connection.execute("ROLLBACK")
                raise DuplicateProjectError(f"Project {project_id} already exists.") from exc
            except Exception:
                self._connection.execute("ROLLBACK")
                raise
        return record

    def get_project(self, project_id: UUID) -> ProjectRecord:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM projects WHERE project_id = ?",
                (str(project_id),),
            ).fetchone()
        if row is None:
            raise ProjectNotFoundError(f"Project {project_id} does not exist.")
        return self._project_from_row(row)

    def list_projects_for_owner(self, owner_user_id: UUID) -> tuple[ProjectRecord, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT p.*
                FROM projects AS p
                INNER JOIN project_owners AS o ON o.project_id = p.project_id
                WHERE o.owner_user_id = ?
                ORDER BY p.created_at DESC, p.project_id ASC
                """,
                (str(owner_user_id),),
            ).fetchall()
        return tuple(self._project_from_row(row) for row in rows)

    def is_project_owner(self, project_id: UUID, owner_user_id: UUID) -> bool:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT 1
                FROM project_owners
                WHERE project_id = ? AND owner_user_id = ?
                """,
                (str(project_id), str(owner_user_id)),
            ).fetchone()
        return row is not None

    def append_revision(
        self,
        command: AppendRevisionCommand,
        created_at: datetime,
    ) -> RevisionRecord:
        document = command.document.with_content_hash()
        assert document.content_hash is not None
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                project_row = self._connection.execute(
                    "SELECT * FROM projects WHERE project_id = ?",
                    (str(command.project_id),),
                ).fetchone()
                if project_row is None:
                    raise ProjectNotFoundError(f"Project {command.project_id} does not exist.")

                current_id = project_row["current_revision_id"]
                current_number = int(project_row["current_revision_number"])
                expected = (
                    None
                    if command.expected_parent_revision_id is None
                    else str(command.expected_parent_revision_id)
                )
                if current_id != expected:
                    raise RevisionConflictError(
                        "expected_parent_revision_id does not match the current project revision."
                    )

                revision_number = current_number + 1
                provisional = RevisionRecord.model_construct(
                    project_id=command.project_id,
                    revision_id=document.revision_id,
                    revision_number=revision_number,
                    parent_revision_id=command.expected_parent_revision_id,
                    created_at=created_at,
                    document=document,
                    plan_document_hash=document.content_hash,
                    source_candidate_id=command.source_candidate_id,
                    note=command.note,
                    generated_outputs=command.generated_outputs,
                    payload_hash="0" * 64,
                )
                payload_hash = provisional.compute_payload_hash()
                record = RevisionRecord(
                    **provisional.model_dump(exclude={"payload_hash"}),
                    payload_hash=payload_hash,
                )
                try:
                    self._connection.execute(
                        """
                        INSERT INTO project_revisions(
                            project_id, revision_id, revision_number, parent_revision_id,
                            created_at, plan_document_json, plan_document_hash,
                            source_candidate_id, note, generated_outputs_json, payload_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(record.project_id),
                            str(record.revision_id),
                            record.revision_number,
                            (
                                None
                                if record.parent_revision_id is None
                                else str(record.parent_revision_id)
                            ),
                            record.created_at.isoformat(),
                            record.document.to_canonical_json(),
                            record.plan_document_hash,
                            (
                                None
                                if record.source_candidate_id is None
                                else str(record.source_candidate_id)
                            ),
                            record.note,
                            json.dumps(
                                [item.model_dump(mode="json") for item in record.generated_outputs],
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            record.payload_hash,
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    raise DuplicateRevisionError(
                        "Revision "
                        f"{record.revision_id} already exists for project {record.project_id}."
                    ) from exc

                self._connection.execute(
                    """
                    UPDATE projects
                    SET current_revision_id = ?, current_revision_number = ?
                    WHERE project_id = ?
                    """,
                    (str(record.revision_id), record.revision_number, str(record.project_id)),
                )
                self._connection.execute("COMMIT")
                return record
            except Exception:
                self._connection.execute("ROLLBACK")
                raise

    def get_revision(self, project_id: UUID, revision_id: UUID) -> RevisionRecord:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM project_revisions
                WHERE project_id = ? AND revision_id = ?
                """,
                (str(project_id), str(revision_id)),
            ).fetchone()
        if row is None:
            raise RevisionNotFoundError(
                f"Revision {revision_id} does not exist for project {project_id}."
            )
        return self._revision_from_row(row)

    def list_revisions(self, project_id: UUID) -> tuple[RevisionRecord, ...]:
        self.get_project(project_id)
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM project_revisions
                WHERE project_id = ?
                ORDER BY revision_number ASC
                """,
                (str(project_id),),
            ).fetchall()
        return tuple(self._revision_from_row(row) for row in rows)

    @staticmethod
    def _project_from_row(row: sqlite3.Row) -> ProjectRecord:
        current = row["current_revision_id"]
        return ProjectRecord(
            project_id=UUID(row["project_id"]),
            name=row["name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            current_revision_id=None if current is None else UUID(current),
            current_revision_number=int(row["current_revision_number"]),
        )

    @staticmethod
    def _revision_from_row(row: sqlite3.Row) -> RevisionRecord:
        try:
            document = PlanDocument.model_validate_json(row["plan_document_json"])
            outputs_data = json.loads(row["generated_outputs_json"])
            outputs = tuple(OutputArtifactRef.model_validate(item) for item in outputs_data)
            parent = row["parent_revision_id"]
            candidate = row["source_candidate_id"]
            return RevisionRecord(
                project_id=UUID(row["project_id"]),
                revision_id=UUID(row["revision_id"]),
                revision_number=int(row["revision_number"]),
                parent_revision_id=None if parent is None else UUID(parent),
                created_at=datetime.fromisoformat(row["created_at"]),
                document=document,
                plan_document_hash=row["plan_document_hash"],
                source_candidate_id=None if candidate is None else UUID(candidate),
                note=row["note"],
                generated_outputs=outputs,
                payload_hash=row["payload_hash"],
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise PersistenceCorruptionError(
                f"Persisted revision {row['revision_id']} failed integrity validation."
            ) from exc

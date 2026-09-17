from __future__ import annotations

import json
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from psycopg import errors
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import ValidationError

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

_PROJECT_TABLE = "ai_vastu_projects"
_REVISION_TABLE = "ai_vastu_project_revisions"
_OWNER_TABLE = "ai_vastu_project_owners"
_CONNECTION_POOL_FACTORY: Any = ConnectionPool


class PostgresProjectRepository:
    """PostgreSQL/Supabase production adapter for immutable project revisions."""

    def __init__(
        self,
        database_url: str,
        *,
        min_pool_size: int = 1,
        max_pool_size: int = 10,
        pool_timeout_seconds: float = 10.0,
    ) -> None:
        if not database_url.strip():
            raise ValueError("database_url cannot be blank.")
        if min_pool_size < 1:
            raise ValueError("min_pool_size must be at least 1.")
        if max_pool_size < min_pool_size:
            raise ValueError("max_pool_size must be >= min_pool_size.")
        if pool_timeout_seconds <= 0:
            raise ValueError("pool_timeout_seconds must be positive.")

        # Vendor types intentionally stay confined to this persistence adapter.
        self._pool: Any = _CONNECTION_POOL_FACTORY(
            conninfo=database_url,
            min_size=min_pool_size,
            max_size=max_pool_size,
            open=True,
            timeout=pool_timeout_seconds,
            check=ConnectionPool.check_connection,
            kwargs={
                "autocommit": True,
                # Supabase transaction-pooler mode doesn't support prepared statements.
                "prepare_threshold": None,
                "row_factory": dict_row,
            },
        )
        self._pool.wait(timeout=pool_timeout_seconds)
        self._verify_schema()

    def close(self) -> None:
        self._pool.close()

    def _verify_schema(self) -> None:
        with self._pool.connection() as connection:
            row = connection.execute(
                """
                SELECT
                    to_regclass('public.ai_vastu_projects') AS projects_table,
                    to_regclass('public.ai_vastu_project_revisions') AS revisions_table,
                    to_regclass('public.ai_vastu_project_owners') AS owners_table
                """
            ).fetchone()
        if row is None:
            raise RuntimeError("PostgreSQL schema verification returned no row.")
        payload = cast(dict[str, Any], row)
        if (
            payload["projects_table"] is None
            or payload["revisions_table"] is None
            or payload["owners_table"] is None
        ):
            raise RuntimeError(
                "PostgreSQL project/auth schema is missing. Apply Phase 18 and Phase 19 "
                "migrations first."
            )

    def create_project(
        self,
        project_id: UUID,
        name: str,
        created_at: datetime,
        owner_user_id: UUID | None = None,
    ) -> ProjectRecord:
        record = ProjectRecord(project_id=project_id, name=name, created_at=created_at)
        try:
            with self._pool.connection() as connection, connection.transaction():
                connection.execute(
                    f"""
                        INSERT INTO {_PROJECT_TABLE}(project_id, name, created_at)
                        VALUES (%s, %s, %s)
                        """,
                    (record.project_id, record.name, record.created_at),
                )
                if owner_user_id is not None:
                    connection.execute(
                        f"""
                            INSERT INTO {_OWNER_TABLE}(project_id, owner_user_id, created_at)
                            VALUES (%s, %s, %s)
                            """,
                        (record.project_id, owner_user_id, record.created_at),
                    )
        except errors.UniqueViolation as exc:
            raise DuplicateProjectError(f"Project {project_id} already exists.") from exc
        return record

    def get_project(self, project_id: UUID) -> ProjectRecord:
        with self._pool.connection() as connection:
            row = connection.execute(
                f"SELECT * FROM {_PROJECT_TABLE} WHERE project_id = %s",
                (project_id,),
            ).fetchone()
        if row is None:
            raise ProjectNotFoundError(f"Project {project_id} does not exist.")
        return self._project_from_row(cast(dict[str, Any], row))

    def list_projects_for_owner(self, owner_user_id: UUID) -> tuple[ProjectRecord, ...]:
        with self._pool.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT p.*
                FROM {_PROJECT_TABLE} AS p
                INNER JOIN {_OWNER_TABLE} AS o ON o.project_id = p.project_id
                WHERE o.owner_user_id = %s
                ORDER BY p.created_at DESC, p.project_id ASC
                """,
                (owner_user_id,),
            ).fetchall()
        return tuple(self._project_from_row(cast(dict[str, Any], row)) for row in rows)

    def is_project_owner(self, project_id: UUID, owner_user_id: UUID) -> bool:
        with self._pool.connection() as connection:
            row = connection.execute(
                f"""
                SELECT 1
                FROM {_OWNER_TABLE}
                WHERE project_id = %s AND owner_user_id = %s
                """,
                (project_id, owner_user_id),
            ).fetchone()
        return row is not None

    def append_revision(
        self,
        command: AppendRevisionCommand,
        created_at: datetime,
    ) -> RevisionRecord:
        document = command.document.with_content_hash()
        assert document.content_hash is not None

        try:
            with self._pool.connection() as connection, connection.transaction():
                project_row = connection.execute(
                    f"""
                        SELECT * FROM {_PROJECT_TABLE}
                        WHERE project_id = %s
                        FOR UPDATE
                        """,
                    (command.project_id,),
                ).fetchone()
                if project_row is None:
                    raise ProjectNotFoundError(f"Project {command.project_id} does not exist.")
                project_payload = cast(dict[str, Any], project_row)
                current_id = project_payload["current_revision_id"]
                current_number = int(project_payload["current_revision_number"])
                if current_id != command.expected_parent_revision_id:
                    raise RevisionConflictError(
                        "expected_parent_revision_id does not match the current project revision."
                    )

                record = self._build_revision_record(
                    command=command,
                    document=document,
                    revision_number=current_number + 1,
                    created_at=created_at,
                )
                connection.execute(
                    f"""
                        INSERT INTO {_REVISION_TABLE}(
                            project_id,
                            revision_id,
                            revision_number,
                            parent_revision_id,
                            created_at,
                            plan_document,
                            plan_document_hash,
                            source_candidate_id,
                            note,
                            generated_outputs,
                            payload_hash
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                    (
                        record.project_id,
                        record.revision_id,
                        record.revision_number,
                        record.parent_revision_id,
                        record.created_at,
                        Jsonb(json.loads(record.document.to_canonical_json())),
                        record.plan_document_hash,
                        record.source_candidate_id,
                        record.note,
                        Jsonb([item.model_dump(mode="json") for item in record.generated_outputs]),
                        record.payload_hash,
                    ),
                )
                connection.execute(
                    f"""
                        UPDATE {_PROJECT_TABLE}
                        SET current_revision_id = %s,
                            current_revision_number = %s
                        WHERE project_id = %s
                        """,
                    (
                        record.revision_id,
                        record.revision_number,
                        record.project_id,
                    ),
                )
                return record
        except errors.UniqueViolation as exc:
            raise DuplicateRevisionError(
                f"Revision {document.revision_id} already exists for project {command.project_id}."
            ) from exc

    def get_revision(self, project_id: UUID, revision_id: UUID) -> RevisionRecord:
        with self._pool.connection() as connection:
            row = connection.execute(
                f"""
                SELECT * FROM {_REVISION_TABLE}
                WHERE project_id = %s AND revision_id = %s
                """,
                (project_id, revision_id),
            ).fetchone()
        if row is None:
            raise RevisionNotFoundError(
                f"Revision {revision_id} does not exist for project {project_id}."
            )
        return self._revision_from_row(cast(dict[str, Any], row))

    def list_revisions(self, project_id: UUID) -> tuple[RevisionRecord, ...]:
        self.get_project(project_id)
        with self._pool.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM {_REVISION_TABLE}
                WHERE project_id = %s
                ORDER BY revision_number ASC
                """,
                (project_id,),
            ).fetchall()
        return tuple(self._revision_from_row(cast(dict[str, Any], row)) for row in rows)

    @staticmethod
    def _build_revision_record(
        *,
        command: AppendRevisionCommand,
        document: PlanDocument,
        revision_number: int,
        created_at: datetime,
    ) -> RevisionRecord:
        assert document.content_hash is not None
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
        return RevisionRecord(
            **provisional.model_dump(exclude={"payload_hash"}),
            payload_hash=provisional.compute_payload_hash(),
        )

    @staticmethod
    def _project_from_row(row: dict[str, Any]) -> ProjectRecord:
        return ProjectRecord(
            project_id=cast(UUID, row["project_id"]),
            name=cast(str, row["name"]),
            created_at=cast(datetime, row["created_at"]),
            current_revision_id=cast(UUID | None, row["current_revision_id"]),
            current_revision_number=int(row["current_revision_number"]),
        )

    @staticmethod
    def _revision_from_row(row: dict[str, Any]) -> RevisionRecord:
        try:
            outputs_payload = row["generated_outputs"]
            if not isinstance(outputs_payload, list):
                raise TypeError("generated_outputs must be a JSON array.")
            outputs = tuple(OutputArtifactRef.model_validate(item) for item in outputs_payload)
            return RevisionRecord(
                project_id=cast(UUID, row["project_id"]),
                revision_id=cast(UUID, row["revision_id"]),
                revision_number=int(row["revision_number"]),
                parent_revision_id=cast(UUID | None, row["parent_revision_id"]),
                created_at=cast(datetime, row["created_at"]),
                document=PlanDocument.model_validate_json(
                    json.dumps(
                        row["plan_document"],
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    )
                ),
                plan_document_hash=cast(str, row["plan_document_hash"]),
                source_candidate_id=cast(UUID | None, row["source_candidate_id"]),
                note=cast(str | None, row["note"]),
                generated_outputs=outputs,
                payload_hash=cast(str, row["payload_hash"]),
            )
        except (ValidationError, ValueError, TypeError, KeyError) as exc:
            raise PersistenceCorruptionError(
                f"Persisted revision {row.get('revision_id')} failed integrity validation."
            ) from exc

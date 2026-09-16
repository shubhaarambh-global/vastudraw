"""Immutable project and revision persistence boundary."""

from .errors import (
    DuplicateProjectError,
    DuplicateRevisionError,
    PersistenceCorruptionError,
    ProjectNotFoundError,
    ProjectStoreConfigurationError,
    ProjectStoreError,
    RevisionConflictError,
    RevisionNotFoundError,
)
from .factory import create_project_repository_from_environment
from .models import (
    PROJECT_STORE_VERSION,
    AppendRevisionCommand,
    OutputArtifactRef,
    ProjectRecord,
    RevisionRecord,
)
from .postgres_repository import PostgresProjectRepository
from .repository import ProjectRepository
from .service import ProjectRevisionService
from .sqlite_repository import SqliteProjectRepository

__all__ = [
    "PROJECT_STORE_VERSION",
    "AppendRevisionCommand",
    "DuplicateProjectError",
    "DuplicateRevisionError",
    "OutputArtifactRef",
    "PersistenceCorruptionError",
    "PostgresProjectRepository",
    "ProjectNotFoundError",
    "ProjectRecord",
    "ProjectRepository",
    "ProjectRevisionService",
    "ProjectStoreConfigurationError",
    "ProjectStoreError",
    "RevisionConflictError",
    "RevisionNotFoundError",
    "RevisionRecord",
    "SqliteProjectRepository",
    "create_project_repository_from_environment",
]

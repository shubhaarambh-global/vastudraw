class ProjectStoreError(RuntimeError):
    """Base class for project/revision persistence failures."""


class ProjectNotFoundError(ProjectStoreError):
    """Raised when a project ID does not exist."""


class RevisionNotFoundError(ProjectStoreError):
    """Raised when a project revision does not exist."""


class DuplicateProjectError(ProjectStoreError):
    """Raised when a project ID already exists."""


class DuplicateRevisionError(ProjectStoreError):
    """Raised when a revision ID already exists for a project."""


class RevisionConflictError(ProjectStoreError):
    """Raised when append-only optimistic concurrency preconditions fail."""


class PersistenceCorruptionError(ProjectStoreError):
    """Raised when persisted canonical content fails integrity checks."""


class ProjectStoreConfigurationError(ProjectStoreError):
    """Raised when production persistence configuration is unsafe."""

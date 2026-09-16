class AuthenticationError(RuntimeError):
    """Raised when an access token cannot be authenticated."""


class AuthConfigurationError(RuntimeError):
    """Raised when production authentication configuration is unsafe or incomplete."""

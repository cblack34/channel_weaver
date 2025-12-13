"""Base exception classes for Channel Weaver."""


class ConfigError(Exception):
    """Base class for user-facing configuration errors.

    All configuration-related exceptions inherit from this class to ensure
    consistent error handling and user messaging throughout the application.
    """
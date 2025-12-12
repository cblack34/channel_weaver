"""Output handler protocols for Channel Weaver."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class OutputHandler(Protocol):
    """Protocol for output handling (console, logging, etc.)."""

    def print(self, message: str, **kwargs) -> None:
        """Print an informational message."""
        ...

    def info(self, message: str) -> None:
        """Print an informational message (alias for print)."""
        ...

    def warning(self, message: str) -> None:
        """Print a warning message."""
        ...

    def error(self, message: str) -> None:
        """Print an error message."""
        ...
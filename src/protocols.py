"""Protocols for dependency injection."""
from typing import Protocol, runtime_checkable

from rich.console import Console


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


class ConsoleOutputHandler:
    """Rich Console-based output handler."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def print(self, message: str, **kwargs) -> None:
        """Print an informational message."""
        self.console.print(message, **kwargs)

    def info(self, message: str) -> None:
        """Print an informational message."""
        self.print(message)

    def warning(self, message: str) -> None:
        """Print a warning message."""
        self.print(f"[yellow]Warning:[/yellow] {message}")

    def error(self, message: str) -> None:
        """Print an error message."""
        self.print(f"[red]Error:[/red] {message}")
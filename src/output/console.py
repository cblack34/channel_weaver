"""Console-based output handler for Channel Weaver."""

from rich.console import Console



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
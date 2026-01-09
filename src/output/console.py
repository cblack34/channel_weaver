"""Console-based output handler for Channel Weaver."""

from rich.console import Console
from rich.table import Table
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.audio.click.models import SectionInfo



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

    def print_section_summary(self, sections: list["SectionInfo"]) -> None:
        """Print a formatted table summarizing detected sections.

        Args:
            sections: List of SectionInfo objects to display
        """
        if not sections:
            self.warning("No sections detected")
            return

        table = Table(title="Section Summary")
        table.add_column("Section", style="cyan", no_wrap=True)
        table.add_column("Start Time", style="magenta")
        table.add_column("Duration", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("BPM", style="blue")

        for section in sections:
            section_name = "02d"
            start_time = self._format_time(section.start_seconds)
            duration = self._format_time(section.duration_seconds)
            section_type = section.section_type.value
            bpm = str(section.bpm) if section.bpm is not None else "none"

            table.add_row(section_name, start_time, duration, section_type, bpm)

        self.console.print()
        self.console.print(table)
        self.console.print()

    def _format_time(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
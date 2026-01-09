"""Output handler protocols for Channel Weaver."""

from pathlib import Path
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


@runtime_checkable
class MetadataWriterProtocol(Protocol):
    """Protocol for writing metadata to audio files."""

    def write_bpm(self, file_path: Path, bpm: int | None) -> bool:
        """Embed BPM metadata into an audio file.

        Args:
            file_path: Path to the audio file to modify
            bpm: BPM value to embed, or None to clear/remove BPM metadata

        Returns:
            True if metadata was successfully written, False otherwise
        """
        ...

    def read_bpm(self, file_path: Path) -> int | None:
        """Read BPM metadata from an audio file.

        Args:
            file_path: Path to the audio file to read

        Returns:
            BPM value if found, None if not present or unreadable
        """
        ...
"""FFmpeg execution wrapper for Channel Weaver."""

import subprocess
from pathlib import Path
from typing import List

from src.exceptions import AudioProcessingError
from src.output import OutputHandler


class FFmpegExecutor:
    """Execute FFmpeg commands with error handling and logging."""

    def __init__(self, output_handler: OutputHandler) -> None:
        """Initialize the FFmpeg executor.

        Args:
            output_handler: Handler for output messages
        """
        self.output_handler = output_handler

    def execute(self, command: List[str], input_path: Path) -> None:
        """Execute an FFmpeg command.

        Args:
            command: FFmpeg command as list of strings
            input_path: Input file path (for error messages)

        Raises:
            AudioProcessingError: If FFmpeg execution fails
        """
        try:
            result = subprocess.run(command, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            self.output_handler.error(f"FFmpeg failed for file {input_path}: {error_msg}")
            raise AudioProcessingError(f"FFmpeg command failed: {error_msg}") from e
"""File discovery and sorting for Channel Weaver."""

import re
from pathlib import Path
from typing import List


class AudioFileDiscovery:
    """Discover and sort WAV files in a directory.

    Handles the discovery of sequential WAV files and sorts them by numeric sequence
    in their filenames for proper processing order.
    """

    def __init__(self, input_dir: Path) -> None:
        """Initialize the file discovery.

        Args:
            input_dir: Directory to search for WAV files
        """
        self.input_dir = input_dir

    def discover_files(self) -> List[Path]:
        """Discover and sort WAV files in the input directory.

        Returns:
            Sorted list of WAV file paths, ordered by numeric sequence in filename
        """
        wav_files = list(self.input_dir.glob("*.[wW][aA][vV]"))
        wav_files.sort(key=self._sort_key)
        return wav_files

    def _sort_key(self, path: Path) -> tuple[int | float, str]:
        """Generate sort key for WAV files based on numeric sequence.

        Args:
            path: File path to generate sort key for

        Returns:
            Tuple of (numeric_value, filename) for sorting WAV files in sequence
        """
        filename = path.stem
        # Find the first sequence of digits
        match = re.search(r'\d+', filename)
        if match:
            num = int(match.group())
        else:
            num = float('inf')  # Put files without numbers at the end
        return (num, filename)
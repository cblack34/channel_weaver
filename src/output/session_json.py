"""JSON session output writer for Channel Weaver."""

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.audio.click.models import SectionInfo


class SessionJsonWriter:
    """Writer for JSON session metadata output."""

    def __init__(self) -> None:
        """Initialize the JSON writer."""
        pass

    def write_session_json(
        self,
        sections: list["SectionInfo"],
        output_path: Path,
        sample_rate: int,
    ) -> bool:
        """Write session metadata as JSON to the specified path.

        Args:
            sections: List of SectionInfo objects
            output_path: Path where to write the JSON file
            sample_rate: Sample rate for time calculations

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate JSON data
            session_data = []
            for section in sections:
                start_seconds = section.get_start_seconds(sample_rate)
                duration_seconds = section.get_duration_seconds(sample_rate)
                
                section_data = {
                    "section": f"section_{section.section_number:02d}",
                    "start_seconds": round(start_seconds, 3),
                    "start_hms": self._format_time(start_seconds),
                    "duration_seconds": round(duration_seconds, 3),
                    "duration_hms": self._format_time(duration_seconds),
                    "type": section.section_type.value,
                    "bpm": section.bpm,
                }
                session_data.append(section_data)

            # Convert to JSON string
            json_content = json.dumps(session_data, indent=2)

            # Write atomically (write to temp file, then rename)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=output_path.parent,
                suffix=".tmp",
                delete=False,
                encoding="utf-8",
            ) as temp_file:
                temp_file.write(json_content)
                temp_path = Path(temp_file.name)

            # Atomic rename
            temp_path.replace(output_path)

            return True

        except Exception:
            # Clean up temp file if it exists
            if "temp_path" in locals():
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass
            return False

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
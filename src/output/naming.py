"""Filename sanitization and path generation for Channel Weaver."""

import re
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """Return a filesystem-safe version of ``name``.

    Leading/trailing whitespace is trimmed, internal whitespace is collapsed, and any
    characters not safe for filesystem use are replaced with underscores.

    Args:
        name: The filename to sanitize

    Returns:
        A sanitized filename safe for filesystem use
    """
    # Trim leading/trailing whitespace
    name = name.strip()
    # Collapse internal whitespace
    name = re.sub(r'\s+', ' ', name)
    # Replace unsafe characters with underscores
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove control characters
    name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', name)
    # Return default name if result is empty
    return name or "track"


def build_output_path(output_dir: Path, channel_num: int, name: str, extension: str = "wav") -> Path:
    """Build a standardized output path for a track.

    Args:
        output_dir: Base output directory
        channel_num: Channel number for prefix
        name: Track name to sanitize
        extension: File extension (default: "wav")

    Returns:
        Complete output path with sanitized filename
    """
    sanitized_name = sanitize_filename(name)
    filename = f"{channel_num:02d}_{sanitized_name}.{extension}"
    return output_dir / filename


def build_bus_output_path(output_dir: Path, file_name: str, extension: str = "wav") -> Path:
    """Build output path for a bus track.

    Args:
        output_dir: Base output directory
        file_name: Bus filename (assumed pre-sanitized)
        extension: File extension (default: "wav")

    Returns:
        Complete output path for bus file
    """
    return output_dir / f"{file_name}.{extension}"
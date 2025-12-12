"""CLI utility functions for Channel Weaver."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def _sanitize_path(path: Path) -> Path:
    """Return a normalized, absolute version of ``path``."""

    return path.expanduser().resolve()


def _default_output_dir(input_path: Path) -> Path:
    """Return a conflict-free default output directory for the given input folder."""

    base_dir = input_path.parent
    base_name = f"{input_path.name}_processed"
    candidate = base_dir / base_name

    suffix = 2
    while candidate.exists():
        candidate = base_dir / f"{base_name}_v{suffix}"
        suffix += 1
    return candidate


def _ensure_output_path(input_path: Path, override: Optional[Path]) -> Path:
    """Determine the effective output directory, respecting user overrides."""

    if override:
        return _sanitize_path(override)
    return _default_output_dir(input_path)


def _determine_temp_dir(output_dir: Path, override: Optional[Path]) -> Path:
    """Select the temporary directory to use for intermediate files."""

    if override:
        return _sanitize_path(override)
    return output_dir / "temp"
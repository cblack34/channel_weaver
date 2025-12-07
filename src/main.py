"""Entry point for the Midas M32 multitrack processor CLI.

This module exposes a Typer-powered command-line interface that wires editable
channel and bus definitions into a validated configuration object and prepares
paths for downstream processing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from src.models import BitDepth, BusConfig, BusSlot, BusType, ChannelAction, ChannelConfig
from src.constants import VERSION


# Channel definitions – list of dicts for easy editing and future config file support
# Any missing channels 1–N (where N is detected channel count) are auto-created as "Ch XX" with action=PROCESS
# Log warnings for auto-created channels to alert users
CHANNELS: list[dict[str, object]] = [
    {"ch": 1, "name": "Kick In"},
    {"ch": 2, "name": "Kick Out"},
    {"ch": 3, "name": "Snare Top"},
    {"ch": 31, "name": "Click", "action": ChannelAction.SKIP},
    {"ch": 32, "name": "Talkback", "action": ChannelAction.SKIP},
]

# Bus definitions – list of dicts, each owns its slot-to-channel mappings and custom file name
BUSES: list[dict[str, object]] = [
    {
        "file_name": "07_Overheads",
        "type": BusType.STEREO,
        "slots": {BusSlot.LEFT: 7, BusSlot.RIGHT: 8},
    },
    {
        "file_name": "15_Room Mics",
        "type": BusType.STEREO,
        "slots": {BusSlot.LEFT: 15, BusSlot.RIGHT: 16},
    },
]


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


app = typer.Typer(add_completion=False, help="Midas M32 multitrack processor")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"Channel Weaver v{VERSION}")
        raise typer.Exit()


@app.command()
def main(
    input_path: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True, help="Directory containing sequential WAV files"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Override the default output directory",
    ),
    bit_depth: BitDepth = typer.Option(BitDepth.FLOAT32, "--bit-depth", help="Target bit depth for output files"),
    temp_dir: Optional[Path] = typer.Option(None, "--temp-dir", file_okay=False, dir_okay=True, resolve_path=True, help="Custom temporary directory"),
    keep_temp: bool = typer.Option(False, "--keep-temp", help="Keep temporary files instead of deleting them"),
    version: bool = typer.Option(
        None, "--version", "-v",
        callback=version_callback,
        is_eager=True,  # Critical: process before other options
        is_flag=True,
        help="Show version and exit."
    ),
) -> None:
    """Process multitrack recordings according to the provided configuration."""

    normalized_input = _sanitize_path(input_path)
    output_dir = _ensure_output_path(normalized_input, output)
    temp_root = _determine_temp_dir(output_dir, temp_dir)

    channels = [ChannelConfig(**channel_dict) for channel_dict in CHANNELS]
    buses = [BusConfig(**bus_dict) for bus_dict in BUSES]

    typer.echo("Midas M32 multitrack processor")
    typer.echo(f"Input directory: {normalized_input}")
    typer.echo(f"Output directory: {output_dir}")
    typer.echo(f"Temporary directory: {temp_root}")
    typer.echo(f"Keep temporary files: {'yes' if keep_temp else 'no'}")
    typer.echo(f"Selected bit depth: {bit_depth.value}")
    typer.echo(f"Loaded {len(channels)} channel definitions and {len(buses)} bus definitions.")

    # Placeholder for future processing logic
    typer.echo("Processing is not yet implemented in this scaffold.")


if __name__ == "__main__":
    app()

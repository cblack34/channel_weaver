"""Entry point for the Midas M32 multitrack processor CLI.

This module exposes a Typer-powered command-line interface that wires editable
channel and bus definitions into a validated configuration object and prepares
paths for downstream processing.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from src.constants import VERSION
from src.exceptions import ConfigError, AudioProcessingError
from src.m32_processor import AudioExtractor, TrackBuilder, ConfigLoader
from src.models import (
    BitDepth
)
from src.types import ChannelDict, BusDict

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Default to WARNING level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Channel definitions – list of dicts for easy editing and future config file support
# Any missing channels 1–N (where N is detected channel count) are auto-created as "Ch XX" with action=PROCESS
# Log warnings for auto-created channels to alert users
CHANNELS: list[ChannelDict] = [
    {"ch": 1, "name": "Kick"},
    {"ch": 2, "name": "Snare Top", "action": "SKIP"},
    {"ch": 21, "name": "Snare Top", "output_ch": 2},
    {"ch": 3, "name": "Hi-Hat"},
    {"ch": 4, "name": "Tom 1"},
    {"ch": 5, "name": "Tom 2"},
    {"ch": 6, "name": "Snare Bottom"},
    {"ch": 7, "name": "Overhead L", "action": "BUS"},
    {"ch": 8, "name": "Overhead R", "action": "BUS"},
    {"ch": 9, "name": "Bass"},
    {"ch": 10, "name": "AG"},
    {"ch": 11, "name": "EG 1"},
    {"ch": 12, "name": "EG 2"},
    {"ch": 13, "name": "Keys"},
    {"ch": 14, "name": "Vox 1"},
    {"ch": 15, "name": "Vox 2"},
    {"ch": 16, "name": "Vox 3"},
    {"ch": 17, "name": "Click"},
    {"ch": 18, "name": "Guide"},
    {"ch": 19, "name": "Loop Left", "action": "BUS"},
    {"ch": 20, "name": "Loop Right", "action": "BUS"},
    # {"ch": 21, "name": "Audience Left", "action": "SKIP"},
    {"ch": 22, "name": "Audience Right", "action": "SKIP"},
    {"ch": 23, "name": "HandHeld"},
    {"ch": 24, "name": "HeadSet"},
    {"ch": 25, "name": "blank", "action": "SKIP"},
    {"ch": 26, "name": "blank", "action": "SKIP"},
    {"ch": 27, "name": "blank", "action": "SKIP"},
    {"ch": 28, "name": "blank", "action": "SKIP"},
    {"ch": 29, "name": "blank", "action": "SKIP"},
    {"ch": 30, "name": "blank", "action": "SKIP"},
    {"ch": 31, "name": "blank", "action": "SKIP"},
    {"ch": 32, "name": "blank", "action": "SKIP"},
]

# Bus definitions – list of dicts, each owns its slot-to-channel mappings and custom file name
BUSES: list[BusDict] = [
    {
        "file_name": "07_Overheads",
        "type": "STEREO",
        "slots": {"LEFT": 7, "RIGHT": 8},
    },
    {
        "file_name": "19_Loop",
        "type": "STEREO",
        "slots": {"LEFT": 19, "RIGHT": 20},
    },
    # {
    #     "file_name": "21_Audience_Right_Mono",
    #     "type": "STEREO",
    #     "slots": {"LEFT": 21, "RIGHT": 22},
    # }
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
    """Handle version flag callback for Typer CLI.

    Args:
        value: Whether the version flag was provided
    """
    if value:
        typer.echo(f"Channel Weaver v{VERSION}")
        raise typer.Exit()


@app.command()
def main(
        input_path: Path = typer.Argument(
            ..., exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True,
            help="Directory containing sequential WAV files"
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
        bit_depth: BitDepth = typer.Option(BitDepth.SOURCE, "--bit-depth",
                                           help="Target bit depth for output files (source=preserve original)"),
        temp_dir: Optional[Path] = typer.Option(None, "--temp-dir", file_okay=False, dir_okay=True, resolve_path=True,
                                                help="Custom temporary directory"),
        keep_temp: bool = typer.Option(False, "--keep-temp", help="Keep temporary files instead of deleting them"),
        version: bool = typer.Option(
            None, "--version", "-v",
            callback=version_callback,
            is_eager=True,  # Critical: process before other options
            is_flag=True,
            help="Show version and exit."
        ),
        verbose: bool = typer.Option(
            False, "--verbose",
            help="Enable verbose debug output"
        ),
) -> None:
    """Process multitrack recordings according to the provided configuration."""

    # Configure logging level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    else:
        logging.getLogger().setLevel(logging.WARNING)

    console = Console()

    normalized_input = _sanitize_path(input_path)
    output_dir = _ensure_output_path(normalized_input, output)
    temp_root = _determine_temp_dir(output_dir, temp_dir)

    try:
        # Initialize AudioExtractor
        extractor = AudioExtractor(
            input_dir=normalized_input,
            temp_dir=temp_root,
            keep_temp=keep_temp,
            console=console,
        )

        # Discover and validate input files
        extractor.discover_and_validate()

        # Get detected channel count for ConfigLoader
        detected_channel_count = extractor.channels

        # Load and validate configuration
        config_loader = ConfigLoader(CHANNELS, BUSES, detected_channel_count=detected_channel_count)
        channels, buses = config_loader.load()

        # Extract segments
        segments = extractor.extract_segments(target_bit_depth=bit_depth)

        # Build tracks
        builder = TrackBuilder(
            sample_rate=extractor.sample_rate,
            bit_depth=bit_depth,
            source_bit_depth=extractor.bit_depth,
            temp_dir=temp_root,
            output_dir=output_dir,
            keep_temp=keep_temp,
            console=console,
        )
        builder.build_tracks(channels, buses, segments)

    except (ConfigError, AudioProcessingError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    finally:
        if not keep_temp and 'extractor' in locals():
            extractor.cleanup()


if __name__ == "__main__":
    app()

"""CLI command implementations for Channel Weaver."""

import logging
from pathlib import Path

import typer
from rich.console import Console

from src.constants import VERSION
from src.exceptions import ConfigError, AudioProcessingError
from src.audio.extractor import AudioExtractor
from src.processing.builder import TrackBuilder
from src.config import ConfigLoader, CHANNELS, BUSES, BitDepth
from src.cli.utils import _sanitize_path, _ensure_output_path, _determine_temp_dir

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Default to WARNING level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def version_callback(value: bool) -> None:
    """Handle version flag callback for Typer CLI.

    Args:
        value: Whether the version flag was provided
    """
    if value:
        typer.echo(f"Channel Weaver v{VERSION}")
        raise typer.Exit()


def main(
        input_path: Path = typer.Argument(
            ..., exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True,
            help="Directory containing sequential WAV files"
        ),
        output: Path | None = typer.Option(
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
        temp_dir: Path | None = typer.Option(None, "--temp-dir", file_okay=False, dir_okay=True, resolve_path=True,
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
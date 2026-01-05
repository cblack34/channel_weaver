"""CLI command implementations for Channel Weaver."""

import logging
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from src.constants import VERSION
from src.exceptions import ConfigError, AudioProcessingError, YAMLConfigError
from src.audio.extractor import AudioExtractor
from src.processing.builder import TrackBuilder
from src.config import ConfigLoader, CHANNELS, BUSES, BitDepth, ProcessingOptions
from src.config.resolver import ConfigResolver
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


def process(
    input_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Directory containing sequential WAV files",
        ),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output", "-o",
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            help="Override the default output directory",
        ),
    ] = None,
    config: Annotated[
        Optional[Path],
        typer.Option(
            "--config", "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="Path to YAML configuration file",
        ),
    ] = None,
    bit_depth: Annotated[
        BitDepth,
        typer.Option(
            "--bit-depth",
            help="Target bit depth for output files (source=preserve original)",
        ),
    ] = BitDepth.SOURCE,
    temp_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--temp-dir",
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            help="Custom temporary directory",
        ),
    ] = None,
    keep_temp: Annotated[
        bool,
        typer.Option(
            "--keep-temp",
            help="Keep temporary files instead of deleting them",
        ),
    ] = False,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", "-v",
            callback=version_callback,
            is_eager=True,
            is_flag=True,
            help="Show version and exit.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Enable verbose debug output",
        ),
    ] = False,
    section_by_click: Annotated[
        bool,
        typer.Option(
            "--section-by-click",
            help="Enable section splitting based on click track analysis",
        ),
    ] = False,
    gap_threshold: Annotated[
        Optional[float],
        typer.Option(
            "--gap-threshold",
            min=0.1,
            help="Minimum gap between sections in seconds (overrides config)",
        ),
    ] = None,
    session_json: Annotated[
        Optional[Path],
        typer.Option(
            "--session-json",
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
            help="Output session metadata as JSON file",
        ),
    ] = None,
) -> None:
    """Process multitrack recordings according to configuration."""

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

        # Resolve and load configuration
        resolver = ConfigResolver(explicit_path=config)
        config_path = resolver.resolve()
        
        if config_path is not None:
            console.print(f"[dim]Using configuration: {config_path}[/dim]")
            config_loader = ConfigLoader.from_yaml(
                config_path,
                detected_channel_count=detected_channel_count,
            )
        else:
            # Use built-in defaults
            config_loader = ConfigLoader(
                CHANNELS,
                BUSES,
                detected_channel_count=detected_channel_count,
            )
        
        channels, buses, section_splitting = config_loader.load()

        # Create and merge processing options
        processing_options = ProcessingOptions(
            section_by_click=section_by_click,
            gap_threshold_seconds=gap_threshold,
            session_json_path=session_json,
        )
        channels, buses, section_splitting = config_loader.merge_processing_options(
            channels, buses, section_splitting, processing_options
        )

        # Extract segments
        segments = extractor.extract_segments(target_bit_depth=bit_depth)

        # Build tracks
        builder = TrackBuilder(
            sample_rate=extractor.sample_rate,  # type: ignore[arg-type]
            bit_depth=bit_depth,
            source_bit_depth=extractor.bit_depth,
            temp_dir=temp_root,
            output_dir=output_dir,
            keep_temp=keep_temp,
            console=console,
        )
        builder.build_tracks(channels, buses, segments)

    except (YAMLConfigError, ConfigError, AudioProcessingError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    finally:
        if not keep_temp and 'extractor' in locals():
            extractor.cleanup()


def init_config(
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output", "-o",
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
            help="Output path for the configuration file",
        ),
    ] = None,
    minimal: Annotated[
        bool,
        typer.Option(
            "--minimal", "-m",
            help="Generate a minimal example configuration",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force", "-f",
            help="Overwrite existing configuration file",
        ),
    ] = False,
) -> None:
    """Generate an example YAML configuration file.
    
    Creates a well-documented configuration file that you can customize
    for your specific multitrack setup.
    """
    from src.config.generator import ConfigGenerator
    console = Console()
    
    # Determine output path
    output_path = output or ConfigResolver.get_default_path()
    
    # Check for existing file
    if output_path.exists() and not force:
        console.print(
            f"[yellow]Configuration file already exists:[/yellow] {output_path}"
        )
        console.print("Use [bold]--force[/bold] to overwrite.")
        raise typer.Exit(code=1)
    
    try:
        if minimal:
            ConfigGenerator.generate_minimal(output_path)
        else:
            generator = ConfigGenerator()
            generator.generate(output_path)
        
        console.print(f"[green]Created configuration file:[/green] {output_path}")
        console.print("\nEdit this file to customize your channel and bus settings.")
        console.print("Then run: [bold]channel-weaver process <input_dir>[/bold]")
        
    except OSError as e:
        console.print(f"[red]Failed to write configuration file:[/red] {e}")
        raise typer.Exit(code=1)


def validate_config(
    config_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="Path to the configuration file to validate",
        ),
    ],
    channel_count: Annotated[
        Optional[int],
        typer.Option(
            "--channels", "-n",
            min=1,
            max=128,
            help="Expected channel count (for full validation)",
        ),
    ] = None,
) -> None:
    """Validate a YAML configuration file.
    
    Checks the configuration file for:
    - Valid YAML syntax
    - Correct schema structure
    - Valid channel and bus definitions
    - Cross-reference validation (if --channels provided)
    """
    from src.config.yaml_source import YAMLConfigSource
    console = Console()
    
    try:
        # Load and parse YAML
        source = YAMLConfigSource(config_path)
        channels_data, buses_data, section_splitting_data, schema_version = source.load()
        
        console.print(f"[dim]Schema version: {schema_version}[/dim]")
        console.print(f"[dim]Channels defined: {len(channels_data)}[/dim]")
        console.print(f"[dim]Buses defined: {len(buses_data)}[/dim]")
        if section_splitting_data:
            console.print("[dim]Section splitting: enabled[/dim]")
        else:
            console.print("[dim]Section splitting: disabled[/dim]")
        
        # Full validation through ConfigLoader
        config_loader = ConfigLoader(
            channels_data,  # type: ignore[arg-type]
            buses_data,  # type: ignore[arg-type]
            detected_channel_count=channel_count,
        )
        channels, buses, section_splitting = config_loader.load()
        
        console.print("\n[green]✓ Configuration is valid[/green]")
        console.print(f"  Channels: {len(channels)}")
        console.print(f"  Buses: {len(buses)}")
        console.print(f"  Section splitting: {'enabled' if section_splitting.enabled else 'disabled'}")
        
        if channel_count:
            console.print(f"  Validated against {channel_count} channels")
        
    except YAMLConfigError as e:
        console.print(f"[red]✗ Configuration error:[/red] {e}")
        raise typer.Exit(code=1)
    except ConfigError as e:
        console.print(f"[red]✗ Validation error:[/red] {e}")
        raise typer.Exit(code=1)
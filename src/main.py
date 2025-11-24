"""Entry point for the Midas M32 multitrack processor CLI.

This module exposes a Typer-powered command-line interface that wires editable
channel and bus definitions into a validated configuration object and prepares
paths for downstream processing.
"""
from __future__ import annotations

from enum import Enum, auto
from pathlib import Path
from typing import Iterable, Optional

import typer
from pydantic import BaseModel, Field, validator


class ChannelAction(Enum):
    """Possible actions that can be taken for a channel."""

    PROCESS = auto()
    BUS = auto()
    SKIP = auto()


class BusSlot(Enum):
    """Slot positions for stereo buses."""

    LEFT = auto()
    RIGHT = auto()


class BusType(Enum):
    """Supported bus types."""

    STEREO = auto()

    def required_slots(self) -> set[BusSlot]:
        """Return the set of slots required for this bus type."""

        if self is BusType.STEREO:
            return {BusSlot.LEFT, BusSlot.RIGHT}
        raise ValueError(f"Unsupported BusType: {self}")


class BitDepth(str, Enum):
    """Selectable bit depths for output files."""

    FLOAT32 = "32float"
    INT24 = "24"
    INT16 = "16"

    def __str__(self) -> str:  # pragma: no cover - convenience for Typer display
        return self.value


class ChannelConfig(BaseModel):
    """User-editable channel configuration entry."""

    ch: int = Field(..., ge=1, description="Channel number (1-based)")
    name: str
    action: ChannelAction = ChannelAction.PROCESS

    @validator("action")
    def validate_action(cls, value: ChannelAction) -> ChannelAction:  # noqa: B902
        return value


class BusConfig(BaseModel):
    """User-editable bus configuration entry."""

    file_name: str = Field(..., description="Custom file name for output, e.g., '07_overheads'")
    type: BusType = BusType.STEREO
    slots: dict[BusSlot, int] = Field(..., description="Slot to channel mapping")

    @validator("slots")
    def validate_slots(cls, value: dict[BusSlot, int], values: dict[str, object]) -> dict[BusSlot, int]:  # noqa: B902
        bus_type = values.get("type", BusType.STEREO)
        if isinstance(bus_type, BusType):
            required = bus_type.required_slots()
            if set(value.keys()) != required:
                raise ValueError(f"{bus_type.name} buses require slots: {', '.join(slot.name for slot in required)}")
        return value


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


class ConfigLoader:
    """Load and validate user-editable channel and bus definitions."""

    def __init__(self, channels_data: Iterable[dict[str, object]], buses_data: Iterable[dict[str, object]]) -> None:
        self._channels_data = list(channels_data)
        self._buses_data = list(buses_data)

    def load_channels(self) -> list[ChannelConfig]:
        """Create channel config models from raw data."""

        return [ChannelConfig(**channel_dict) for channel_dict in self._channels_data]

    def load_buses(self) -> list[BusConfig]:
        """Create bus config models from raw data."""

        return [BusConfig(**bus_dict) for bus_dict in self._buses_data]


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
) -> None:
    """Process multitrack recordings according to the provided configuration."""

    normalized_input = _sanitize_path(input_path)
    output_dir = _ensure_output_path(normalized_input, output)
    temp_root = _determine_temp_dir(output_dir, temp_dir)

    config_loader = ConfigLoader(CHANNELS, BUSES)
    channels = config_loader.load_channels()
    buses = config_loader.load_buses()

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

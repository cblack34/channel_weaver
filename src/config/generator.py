"""Configuration file generator for Channel Weaver."""

from pathlib import Path

import yaml

from src.config.defaults import CHANNELS, BUSES


# Template header with documentation
CONFIG_HEADER = """\
# Channel Weaver Configuration File
# ===================================
#
# This file defines how input audio channels are processed and combined.
#
# CHANNELS SECTION
# ----------------
# Each channel entry defines processing for an input channel:
#
#   ch:        (required) Input channel number (1-32, 1-based indexing)
#   name:      (required) Display name for the channel (used in output filenames)
#   action:    (optional) Processing action - one of:
#              - PROCESS: Extract and output as individual mono file (default)
#              - SKIP: Ignore this channel entirely
#              - BUS: Reserve for stereo bus mixing (don't output individually)
#   output_ch: (optional) Override output channel number in filename
#              Defaults to the input channel number (ch)
#
# Any channels not listed here will be auto-created with action=PROCESS
# and name="Channel N" where N is the channel number.
#
# BUSES SECTION
# -------------
# Each bus entry combines multiple channels into a stereo output:
#
#   file_name: (required) Output filename (without .wav extension)
#   type:      (optional) Bus type - currently only STEREO supported
#   slots:     (required) Mapping of slot positions to input channels:
#              - LEFT: Channel number for left audio
#              - RIGHT: Channel number for right audio
#
# Channels assigned to buses should have action=BUS to avoid duplicate output.
#
# Example with all options:
#
#   channels:
#     - ch: 1
#       name: Kick
#       action: PROCESS
#     - ch: 7
#       name: Overhead L
#       action: BUS
#
#   buses:
#     - file_name: 07_Overheads
#       type: STEREO
#       slots:
#         LEFT: 7
#         RIGHT: 8

"""


class ConfigGenerator:
    """Generate example YAML configuration files.

    This class creates well-documented configuration files based on
    the default configuration or custom channel/bus definitions.
    """

    def __init__(
        self,
        channels: list[dict] | None = None,
        buses: list[dict] | None = None,
    ) -> None:
        """Initialize the config generator.

        Args:
            channels: Channel configurations (uses defaults if None)
            buses: Bus configurations (uses defaults if None)
        """
        self.channels = channels if channels is not None else CHANNELS
        self.buses = buses if buses is not None else BUSES

    def generate(self, output_path: Path, *, include_header: bool = True) -> None:
        """Generate a YAML configuration file.

        Args:
            output_path: Path where the config file will be written
            include_header: Whether to include documentation header

        Raises:
            OSError: If the file cannot be written
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build config dictionary
        config = {
            'schema_version': 1,
            'channels': self.channels,
            'buses': self.buses,
        }

        # Generate YAML content
        yaml_content = yaml.safe_dump(
            config,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2,
            width=80,
        )

        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            if include_header:
                f.write(CONFIG_HEADER)
            f.write(yaml_content)

    @classmethod
    def generate_minimal(cls, output_path: Path) -> None:
        """Generate a minimal example configuration.

        Creates a config with just essential examples, suitable for
        users who want to start from scratch.

        Args:
            output_path: Path where the config file will be written
        """
        minimal_channels = [
            {"ch": 1, "name": "Kick"},
            {"ch": 2, "name": "Snare"},
            {"ch": 3, "name": "Hi-Hat"},
            {"ch": 4, "name": "Overhead L", "action": "BUS"},
            {"ch": 5, "name": "Overhead R", "action": "BUS"},
        ]

        minimal_buses = [
            {
                "file_name": "04_Overheads",
                "type": "STEREO",
                "slots": {"LEFT": 4, "RIGHT": 5},
            }
        ]

        generator = cls(channels=minimal_channels, buses=minimal_buses)
        generator.generate(output_path)
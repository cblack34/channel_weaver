"""YAML configuration source for Channel Weaver."""

from pathlib import Path
from typing import Any

import yaml

from src.config.protocols import CURRENT_SCHEMA_VERSION
from src.exceptions import YAMLConfigError


class YAMLConfigSource:
    """Load configuration from YAML files.

    Implements the ConfigSource protocol for YAML file loading.

    Attributes:
        config_path: Path to the YAML configuration file
    """

    def __init__(self, config_path: Path) -> None:
        """Initialize the YAML config source.

        Args:
            config_path: Path to the YAML configuration file

        Raises:
            YAMLConfigError: If the file does not exist
        """
        self._config_path = config_path
        if not config_path.exists():
            raise YAMLConfigError(f"Configuration file not found: {config_path}")
        if not config_path.is_file():
            raise YAMLConfigError(f"Configuration path is not a file: {config_path}")

    @property
    def source_description(self) -> str:
        """Human-readable description of the config source."""
        return f"YAML file: {self._config_path}"

    def load(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None, int]:
        """Load and parse the YAML configuration file.

        Returns:
            Tuple of (channels_data, buses_data, schema_version)

        Raises:
            YAMLConfigError: If YAML parsing fails or structure is invalid
        """
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            error_msg = f"Failed to parse YAML configuration: {e}"
            if hasattr(e, 'problem_mark') and e.problem_mark is not None:
                mark = e.problem_mark
                error_msg += f" (line {mark.line + 1}, column {mark.column + 1})"
            raise YAMLConfigError(error_msg) from e

        if data is None:
            raise YAMLConfigError("Configuration file is empty")

        if not isinstance(data, dict):
            raise YAMLConfigError(
                f"Configuration must be a YAML mapping, got {type(data).__name__}"
            )

        return self._extract_config(data)

    def _extract_config(
        self, data: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None, int]:
        """Extract channels, buses, section_splitting, and schema version from parsed YAML.

        Args:
            data: Parsed YAML data as a dictionary

        Returns:
            Tuple of (channels_data, buses_data, section_splitting_data, schema_version)

        Raises:
            YAMLConfigError: If required sections are missing or invalid
        """
        # Extract and validate schema version
        schema_version = data.get('schema_version', 1)
        if not isinstance(schema_version, int):
            raise YAMLConfigError(
                f"'schema_version' must be an integer, got {type(schema_version).__name__}"
            )
        if schema_version > CURRENT_SCHEMA_VERSION:
            raise YAMLConfigError(
                f"Configuration schema version {schema_version} is not supported. "
                f"Maximum supported version is {CURRENT_SCHEMA_VERSION}. "
                "Please update Channel Weaver."
            )

        # Extract channels (required)
        channels = data.get('channels')
        if channels is None:
            raise YAMLConfigError("Missing required 'channels' section in configuration")
        if not isinstance(channels, list):
            raise YAMLConfigError(
                f"'channels' must be a list, got {type(channels).__name__}"
            )

        # Extract buses (optional, default to empty list)
        buses = data.get('buses', [])
        if not isinstance(buses, list):
            raise YAMLConfigError(
                f"'buses' must be a list, got {type(buses).__name__}"
            )

        # Extract section_splitting (optional, default to None)
        section_splitting = data.get('section_splitting')
        if section_splitting is not None and not isinstance(section_splitting, dict):
            raise YAMLConfigError(
                f"'section_splitting' must be a mapping, got {type(section_splitting).__name__}"
            )

        return channels, buses, section_splitting, schema_version
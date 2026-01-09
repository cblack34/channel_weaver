"""Default configuration source for Channel Weaver."""

from typing import Any

from src.config.defaults import CHANNELS, BUSES
from src.config.protocols import CURRENT_SCHEMA_VERSION


class DefaultConfigSource:
    """Provide built-in default configuration.

    Implements the ConfigSource protocol using the Python defaults
    defined in src/config/defaults.py.
    """

    @property
    def source_description(self) -> str:
        """Human-readable description of the config source."""
        return "built-in defaults"

    def load(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None, int]:
        """Load the built-in default configuration.

        Returns:
            Tuple of (channels_data, buses_data, section_splitting_data, schema_version)
        """
        return CHANNELS, BUSES, None, CURRENT_SCHEMA_VERSION  # type: ignore[return-value]
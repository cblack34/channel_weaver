"""Protocol definitions for configuration sources."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConfigSource(Protocol):
    """Protocol for configuration data sources.

    This protocol defines the interface that all configuration sources
    must implement. Following the Dependency Inversion Principle, the
    ConfigLoader depends on this abstraction rather than concrete
    implementations.

    Implementations include:
    - YAMLConfigSource: Load from YAML files
    - DefaultConfigSource: Built-in Python defaults
    - (Future) JSONConfigSource, TOMLConfigSource, etc.
    """

    def load(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        """Load configuration data from the source.

        Returns:
            Tuple of (channels_data, buses_data, schema_version) where:
            - channels_data: List of channel configuration dictionaries
            - buses_data: List of bus configuration dictionaries
            - schema_version: Schema version number (1 for built-in defaults)

        Raises:
            ConfigError: If configuration cannot be loaded or is invalid
        """
        ...

    @property
    def source_description(self) -> str:
        """Human-readable description of the config source.

        Returns:
            Description string for logging/error messages
            e.g., "YAML file: /path/to/config.yaml" or "built-in defaults"
        """
        ...


# Current supported schema version
CURRENT_SCHEMA_VERSION = 1
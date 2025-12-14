"""Configuration path resolution for Channel Weaver."""

from pathlib import Path


# Default config file names (in order of preference)
DEFAULT_CONFIG_NAMES = [
    "channel_weaver.yaml",
    "channel_weaver.yml",
]


class ConfigResolver:
    """Resolve configuration file paths.

    Resolution order (first match wins):
    1. Explicit path provided via --config CLI option
    2. Config file in current working directory
    3. Fall back to built-in defaults (no file)

    Note: Configuration files are expected to be project-specific,
    so we only search the current working directory, not user home
    or global locations.
    """

    def __init__(self, explicit_path: Path | None = None) -> None:
        """Initialize the config resolver.

        Args:
            explicit_path: Explicitly provided config path (highest priority)
        """
        self.explicit_path = explicit_path

    def resolve(self) -> Path | None:
        """Resolve the configuration file path.

        Returns:
            Path to the config file, or None if using built-in defaults

        Raises:
            FileNotFoundError: If explicit_path is provided but doesn't exist
        """
        # 1. Explicit path (highest priority)
        if self.explicit_path is not None:
            if not self.explicit_path.exists():
                raise FileNotFoundError(
                    f"Configuration file not found: {self.explicit_path}"
                )
            return self.explicit_path

        # 2. Current working directory
        cwd_config = self._find_in_directory(Path.cwd())
        if cwd_config is not None:
            return cwd_config

        # 3. No config file found - will use built-in defaults
        return None

    def _find_in_directory(self, directory: Path) -> Path | None:
        """Search for a config file in the given directory.

        Args:
            directory: Directory to search

        Returns:
            Path to found config file, or None if not found
        """
        for name in DEFAULT_CONFIG_NAMES:
            config_path = directory / name
            if config_path.is_file():
                return config_path
        return None

    @staticmethod
    def get_default_path() -> Path:
        """Get the default path for creating new config files.

        Returns:
            Path in current working directory with primary config name
        """
        return Path.cwd() / DEFAULT_CONFIG_NAMES[0]
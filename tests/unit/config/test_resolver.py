"""Tests for configuration path resolver."""

import pytest
from pathlib import Path
from unittest.mock import patch

from src.config.resolver import ConfigResolver, DEFAULT_CONFIG_NAMES


class TestConfigResolver:
    """Test the ConfigResolver class."""

    def test_init_no_explicit_path(self):
        """Test initialization without explicit path."""
        resolver = ConfigResolver()
        assert resolver.explicit_path is None

    def test_init_with_explicit_path(self):
        """Test initialization with explicit path."""
        path = Path("test.yaml")
        resolver = ConfigResolver(explicit_path=path)
        assert resolver.explicit_path == path

    def test_resolve_explicit_path_exists(self, tmp_path):
        """Test resolving with explicit path that exists."""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text("test: config")

        resolver = ConfigResolver(explicit_path=config_file)
        result = resolver.resolve()

        assert result == config_file

    def test_resolve_explicit_path_not_exists(self, tmp_path):
        """Test resolving with explicit path that doesn't exist."""
        config_file = tmp_path / "nonexistent.yaml"

        resolver = ConfigResolver(explicit_path=config_file)

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            resolver.resolve()

    def test_resolve_cwd_config_found(self, tmp_path):
        """Test resolving finds config in current working directory."""
        # Create a config file in tmp_path
        config_file = tmp_path / DEFAULT_CONFIG_NAMES[0]
        config_file.write_text("channels: []")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            resolver = ConfigResolver()
            result = resolver.resolve()

            assert result == config_file

    def test_resolve_cwd_config_not_found(self, tmp_path):
        """Test resolving returns None when no config in current directory."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            resolver = ConfigResolver()
            result = resolver.resolve()

            assert result is None

    def test_resolve_preference_order(self, tmp_path):
        """Test that explicit path takes precedence over CWD config."""
        # Create both explicit and CWD config files
        explicit_file = tmp_path / "explicit.yaml"
        explicit_file.write_text("explicit: config")

        cwd_file = tmp_path / DEFAULT_CONFIG_NAMES[0]
        cwd_file.write_text("cwd: config")

        resolver = ConfigResolver(explicit_path=explicit_file)
        result = resolver.resolve()

        assert result == explicit_file

    def test_find_in_directory_finds_first_match(self, tmp_path):
        """Test _find_in_directory returns first matching config file."""
        # Create multiple config files
        yaml_file = tmp_path / DEFAULT_CONFIG_NAMES[0]  # channel_weaver.yaml
        yaml_file.write_text("yaml: config")

        yml_file = tmp_path / DEFAULT_CONFIG_NAMES[1]  # channel_weaver.yml
        yml_file.write_text("yml: config")

        resolver = ConfigResolver()
        result = resolver._find_in_directory(tmp_path)

        # Should return the first one in DEFAULT_CONFIG_NAMES order
        assert result == yaml_file

    def test_find_in_directory_finds_second_when_first_missing(self, tmp_path):
        """Test _find_in_directory finds second config when first doesn't exist."""
        # Only create the .yml file
        yml_file = tmp_path / DEFAULT_CONFIG_NAMES[1]
        yml_file.write_text("yml: config")

        resolver = ConfigResolver()
        result = resolver._find_in_directory(tmp_path)

        assert result == yml_file

    def test_find_in_directory_none_found(self, tmp_path):
        """Test _find_in_directory returns None when no config files exist."""
        resolver = ConfigResolver()
        result = resolver._find_in_directory(tmp_path)

        assert result is None

    def test_find_in_directory_skips_directories(self, tmp_path):
        """Test _find_in_directory only finds files, not directories."""
        # Create a directory with a config name
        config_dir = tmp_path / DEFAULT_CONFIG_NAMES[0]
        config_dir.mkdir()

        resolver = ConfigResolver()
        result = resolver._find_in_directory(tmp_path)

        assert result is None

    def test_get_default_path(self):
        """Test get_default_path returns correct default path."""
        with patch("pathlib.Path.cwd", return_value=Path("/test/cwd")):
            default_path = ConfigResolver.get_default_path()

            expected = Path("/test/cwd") / DEFAULT_CONFIG_NAMES[0]
            assert default_path == expected
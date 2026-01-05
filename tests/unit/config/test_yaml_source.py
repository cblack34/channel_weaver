"""Tests for YAML configuration source."""

import pytest
from pathlib import Path

from src.config.yaml_source import YAMLConfigSource, YAMLConfigError


class TestYAMLConfigSource:
    """Tests for YAMLConfigSource class."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Test loading a valid YAML configuration."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
schema_version: 1
channels:
  - ch: 1
    name: Kick
  - ch: 2
    name: Snare
buses:
  - file_name: 01_Stereo
    type: STEREO
    slots:
      LEFT: 1
      RIGHT: 2
""")
        source = YAMLConfigSource(config_file)
        channels, buses, section_splitting, version = source.load()

        assert len(channels) == 2
        assert channels[0]["ch"] == 1
        assert channels[0]["name"] == "Kick"
        assert len(buses) == 1
        assert buses[0]["file_name"] == "01_Stereo"
        assert version == 1

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Test loading from non-existent file."""
        with pytest.raises(YAMLConfigError, match="not found"):
            YAMLConfigSource(tmp_path / "missing.yaml")

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        """Test loading invalid YAML syntax."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("channels:\n  - ch: 1\n  name: broken")

        source = YAMLConfigSource(config_file)
        with pytest.raises(YAMLConfigError, match="Failed to parse"):
            source.load()

    def test_load_missing_channels_section(self, tmp_path: Path) -> None:
        """Test loading config without channels section."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("schema_version: 1\nbuses: []")

        source = YAMLConfigSource(config_file)
        with pytest.raises(YAMLConfigError, match="Missing required 'channels'"):
            source.load()

    def test_load_optional_buses(self, tmp_path: Path) -> None:
        """Test loading config without buses section (optional)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("schema_version: 1\nchannels:\n  - ch: 1\n    name: Kick")

        source = YAMLConfigSource(config_file)
        channels, buses, section_splitting, version = source.load()

        assert len(channels) == 1
        assert buses == []
        assert version == 1

    def test_load_unsupported_schema_version(self, tmp_path: Path) -> None:
        """Test loading config with future schema version."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("schema_version: 999\nchannels:\n  - ch: 1\n    name: Kick")

        source = YAMLConfigSource(config_file)
        with pytest.raises(YAMLConfigError, match="not supported"):
            source.load()

    def test_source_description(self, tmp_path: Path) -> None:
        """Test source_description property."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("schema_version: 1\nchannels:\n  - ch: 1\n    name: Kick")

        source = YAMLConfigSource(config_file)
        assert "YAML file" in source.source_description
        assert str(config_file) in source.source_description
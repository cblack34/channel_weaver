"""Tests for configuration file generator."""

from pathlib import Path

import yaml

from src.config.generator import ConfigGenerator


class TestConfigGenerator:
    """Tests for ConfigGenerator class."""

    def test_generate_default_config(self, tmp_path: Path) -> None:
        """Test generating config with defaults."""
        output_file = tmp_path / "config.yaml"
        generator = ConfigGenerator()
        generator.generate(output_file)

        assert output_file.exists()

        # Verify it's valid YAML
        with open(output_file) as f:
            data = yaml.safe_load(f)

        assert "schema_version" in data
        assert data["schema_version"] == 1
        assert "channels" in data
        assert "buses" in data

    def test_generate_minimal_config(self, tmp_path: Path) -> None:
        """Test generating minimal config."""
        output_file = tmp_path / "config.yaml"
        ConfigGenerator.generate_minimal(output_file)

        assert output_file.exists()

        with open(output_file) as f:
            data = yaml.safe_load(f)

        assert len(data["channels"]) == 5
        assert len(data["buses"]) == 1

    def test_generate_includes_header(self, tmp_path: Path) -> None:
        """Test that generated file includes documentation header."""
        output_file = tmp_path / "config.yaml"
        generator = ConfigGenerator()
        generator.generate(output_file)

        content = output_file.read_text()
        assert "# Channel Weaver Configuration File" in content

    def test_generate_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test that generate creates parent directories."""
        output_file = tmp_path / "nested" / "deep" / "config.yaml"
        generator = ConfigGenerator()
        generator.generate(output_file)

        assert output_file.exists()
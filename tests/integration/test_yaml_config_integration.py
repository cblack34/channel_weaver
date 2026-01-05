"""Integration tests for YAML configuration loading."""

from pathlib import Path

from src.config import ConfigLoader
from src.config.yaml_source import YAMLConfigSource


class TestYAMLConfigIntegration:
    """Integration tests for YAML config with ConfigLoader."""

    def test_full_config_load_and_validate(self, tmp_path: Path) -> None:
        """Test loading YAML config through full validation pipeline."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
schema_version: 1
channels:
  - ch: 1
    name: Kick
  - ch: 2
    name: Snare
  - ch: 3
    name: Overhead L
    action: BUS
  - ch: 4
    name: Overhead R
    action: BUS
buses:
  - file_name: 03_Overheads
    type: STEREO
    slots:
      LEFT: 3
      RIGHT: 4
""")

        source = YAMLConfigSource(config_file)
        loader = ConfigLoader.from_source(
            source,
            detected_channel_count=4,
        )
        channels, buses, section_splitting = loader.load()

        assert len(channels) == 4
        assert len(buses) == 1

        # Verify channel validation
        kick = next(ch for ch in channels if ch.ch == 1)
        assert kick.name == "Kick"

        # Verify bus validation
        assert buses[0].file_name == "03_Overheads"
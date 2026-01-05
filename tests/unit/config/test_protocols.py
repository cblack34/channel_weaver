"""Tests for config source protocols."""


from src.config.protocols import CURRENT_SCHEMA_VERSION


class TestConfigSourceProtocol:
    """Tests for ConfigSource protocol compliance."""

    def test_yaml_source_implements_protocol(self) -> None:
        """Test that YAMLConfigSource implements ConfigSource."""
        from src.config.yaml_source import YAMLConfigSource

        assert isinstance(YAMLConfigSource, type)
        # Protocol check happens at instantiation with valid file

    def test_default_source_implements_protocol(self) -> None:
        """Test that DefaultConfigSource implements ConfigSource."""
        from src.config.default_source import DefaultConfigSource

        source = DefaultConfigSource()
        assert hasattr(source, 'load')
        assert hasattr(source, 'source_description')

        channels, buses, section_splitting, version = source.load()
        assert isinstance(channels, list)
        assert isinstance(buses, list)
        assert section_splitting is None
        assert version == CURRENT_SCHEMA_VERSION
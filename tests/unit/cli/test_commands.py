"""Unit tests for CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_mock import MockerFixture

from src.cli.commands import version_callback, process, init_config, validate_config
from src.config.enums import BitDepth


class TestVersionCallback:
    """Tests for version_callback function."""

    def test_version_callback_true(self, mocker: MockerFixture) -> None:
        """Test version_callback with True value."""
        mock_echo = mocker.patch("src.cli.commands.typer.echo")
        # Mock typer.Exit to raise SystemExit when called
        mock_exit = mocker.patch("src.cli.commands.typer.Exit")
        mock_exit.side_effect = SystemExit()

        with pytest.raises(SystemExit):
            version_callback(True)

        mock_echo.assert_called_once()
        call_args = mock_echo.call_args[0][0]
        assert "Channel Weaver v" in call_args
        mock_exit.assert_called_once()

    def test_version_callback_false(self) -> None:
        """Test version_callback with False value does nothing."""
        # Should not raise or do anything
        version_callback(False)


class TestMainCommand:
    """Tests for main command function."""

    @pytest.fixture
    def mock_dependencies(self, mocker: MockerFixture) -> dict:
        """Set up common mocks for main command tests."""
        mocks = {}

        # Mock CLI utils
        mocks["sanitize"] = mocker.patch("src.cli.commands._sanitize_path")
        mocks["ensure_output"] = mocker.patch("src.cli.commands._ensure_output_path")
        mocks["determine_temp"] = mocker.patch("src.cli.commands._determine_temp_dir")

        # Mock core components
        mocks["extractor"] = mocker.patch("src.cli.commands.AudioExtractor")
        mocks["config_loader"] = mocker.patch("src.cli.commands.ConfigLoader")
        mocks["builder"] = mocker.patch("src.cli.commands.TrackBuilder")

        # Mock ConfigResolver to return None (use defaults path)
        # This ensures tests use the constructor path instead of from_yaml
        mocks["config_resolver"] = mocker.patch("src.cli.commands.ConfigResolver")
        mocks["config_resolver"].return_value.resolve.return_value = None

        # Configure default return values for ConfigLoader paths
        # Both constructor and from_yaml() classmethod need to return instances with load() method
        mocks["config_loader"].return_value.load.return_value = ([], [], None)
        mocks["config_loader"].from_yaml.return_value.load.return_value = ([], [], None)

        # Mock console
        mocks["console"] = mocker.patch("src.cli.commands.Console")

        return mocks

    def test_main_success_path(
        self,
        tmp_path: Path,
        mock_dependencies: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test successful execution of main command."""
        # Set up mocks
        mocks = mock_dependencies

        # Configure path utilities
        input_path = tmp_path / "input"
        output_path = tmp_path / "output"
        temp_path = tmp_path / "temp"

        mocks["sanitize"].return_value = input_path
        mocks["ensure_output"].return_value = output_path
        mocks["determine_temp"].return_value = temp_path

        # Configure extractor
        mock_extractor_instance = mocks["extractor"].return_value
        mock_extractor_instance.channels = 8
        mock_extractor_instance.sample_rate = 44100
        mock_extractor_instance.bit_depth = BitDepth.INT24
        mock_extractor_instance.discover_and_validate.return_value = None
        mock_extractor_instance.extract_segments.return_value = {}
        mock_extractor_instance.cleanup.return_value = None

        # Configure config loader
        mock_config_instance = mocks["config_loader"].return_value
        mock_config_instance.load.return_value = ([], [], None)  # empty channels, buses, and section_splitting

        # Configure builder
        mock_builder_instance = mocks["builder"].return_value
        mock_builder_instance.build_tracks.return_value = None

        # Execute main command
        process(
            input_path=input_path,
            output=None,
            bit_depth=BitDepth.INT16,
            temp_dir=None,
            keep_temp=False,
            version=False,
            verbose=False,
        )

        # Verify path utilities were called
        mocks["sanitize"].assert_called_once_with(input_path)
        mocks["ensure_output"].assert_called_once_with(input_path, None)
        mocks["determine_temp"].assert_called_once_with(output_path, None)

        # Verify extractor was created and used
        mocks["extractor"].assert_called_once_with(
            input_dir=input_path,
            temp_dir=temp_path,
            keep_temp=False,
            console=mocks["console"].return_value,
        )
        mock_extractor_instance.discover_and_validate.assert_called_once()
        mock_extractor_instance.extract_segments.assert_called_once_with(target_bit_depth=BitDepth.INT16)

        # Verify config loader was created and used
        mocks["config_loader"].assert_called_once()
        # Should be called with CHANNELS, BUSES, and detected_channel_count
        call_args = mocks["config_loader"].call_args
        assert call_args[1]["detected_channel_count"] == 8
        mock_config_instance.load.assert_called_once()

        # Verify builder was created and used
        mocks["builder"].assert_called_once_with(
            sample_rate=44100,
            bit_depth=BitDepth.INT16,
            source_bit_depth=BitDepth.INT24,
            temp_dir=temp_path,
            output_dir=output_path,
            keep_temp=False,
            console=mocks["console"].return_value,
        )
        mock_builder_instance.build_tracks.assert_called_once_with([], [], {})

        # Verify cleanup was called
        mock_extractor_instance.cleanup.assert_called_once()

    def test_main_with_verbose_flag(
        self,
        tmp_path: Path,
        mock_dependencies: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test main command with verbose flag enables debug logging."""
        mocks = mock_dependencies

        # Set up minimal mocks to avoid full execution
        mocks["sanitize"].return_value = tmp_path / "input"
        mocks["ensure_output"].return_value = tmp_path / "output"
        mocks["determine_temp"].return_value = tmp_path / "temp"

        mock_extractor_instance = mocks["extractor"].return_value
        mock_extractor_instance.channels = 2
        mock_extractor_instance.cleanup.return_value = None

        mocks["config_loader"].return_value.load.return_value = ([], [])

        # Mock logging
        mock_logger = mocker.patch("src.cli.commands.logger")

        with patch("src.cli.commands.AudioExtractor") as mock_extractor_class:
            mock_extractor_class.side_effect = Exception("Stop execution")

            with pytest.raises(Exception, match="Stop execution"):
                process(
                    input_path=tmp_path / "input",
                    output=None,
                    bit_depth=BitDepth.FLOAT32,
                    temp_dir=None,
                    keep_temp=False,
                    version=False,
                    verbose=True,
                )

        # Verify debug logging was enabled
        mock_logger.debug.assert_called_with("Verbose logging enabled")

    def test_main_config_error_handling(
        self,
        tmp_path: Path,
        mock_dependencies: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test main command handles ConfigError gracefully."""
        mocks = mock_dependencies

        # Set up mocks
        mocks["sanitize"].return_value = tmp_path / "input"
        mocks["ensure_output"].return_value = tmp_path / "output"
        mocks["determine_temp"].return_value = tmp_path / "temp"

        mock_extractor_instance = mocks["extractor"].return_value
        mock_extractor_instance.channels = 4
        mock_extractor_instance.cleanup.return_value = None

        # Make config loader raise ConfigError
        from src.exceptions import ConfigError
        mocks["config_loader"].return_value.load.side_effect = ConfigError("Invalid config")

        mock_console = mocks["console"].return_value
        # Mock typer.Exit to raise SystemExit
        mock_exit = mocker.patch("src.cli.commands.typer.Exit")
        mock_exit.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            process(
                input_path=tmp_path / "input",
                output=None,
                bit_depth=BitDepth.INT24,
                temp_dir=None,
                keep_temp=False,
                version=False,
                verbose=False,
            )

        # Verify error was printed
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "[red]Error:[/red]" in call_args
        assert "Invalid config" in call_args

        # Verify typer.Exit was called with code 1
        mock_exit.assert_called_once_with(code=1)

    def test_main_audio_processing_error_handling(
        self,
        tmp_path: Path,
        mock_dependencies: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test main command handles AudioProcessingError gracefully."""
        mocks = mock_dependencies

        # Set up mocks
        mocks["sanitize"].return_value = tmp_path / "input"
        mocks["ensure_output"].return_value = tmp_path / "output"
        mocks["determine_temp"].return_value = tmp_path / "temp"

        mock_extractor_instance = mocks["extractor"].return_value
        mock_extractor_instance.channels = 6
        mock_extractor_instance.cleanup.return_value = None

        # Make extractor raise AudioProcessingError
        from src.exceptions import AudioProcessingError
        mock_extractor_instance.discover_and_validate.side_effect = AudioProcessingError("Audio processing failed")

        mock_console = mocks["console"].return_value
        # Mock typer.Exit to raise SystemExit
        mock_exit = mocker.patch("src.cli.commands.typer.Exit")
        mock_exit.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            process(
                input_path=tmp_path / "input",
                output=None,
                bit_depth=BitDepth.SOURCE,
                temp_dir=None,
                keep_temp=False,
                version=False,
                verbose=False,
            )

        # Verify error was printed
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "[red]Error:[/red]" in call_args
        assert "Audio processing failed" in call_args

        # Verify typer.Exit was called with code 1
        mock_exit.assert_called_once_with(code=1)

    def test_main_cleanup_called_on_error(
        self,
        tmp_path: Path,
        mock_dependencies: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test that cleanup is called even when errors occur."""
        mocks = mock_dependencies

        # Set up mocks
        mocks["sanitize"].return_value = tmp_path / "input"
        mocks["ensure_output"].return_value = tmp_path / "output"
        mocks["determine_temp"].return_value = tmp_path / "temp"

        mock_extractor_instance = mocks["extractor"].return_value
        mock_extractor_instance.channels = 2
        mock_extractor_instance.cleanup.return_value = None

        # Make config loader raise error
        from src.exceptions import ConfigError
        mocks["config_loader"].return_value.load.side_effect = ConfigError("Config error")

        # Mock typer.Exit to raise SystemExit
        mock_exit = mocker.patch("src.cli.commands.typer.Exit")
        mock_exit.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            process(
                input_path=tmp_path / "input",
                output=None,
                bit_depth=BitDepth.FLOAT32,
                temp_dir=None,
                keep_temp=False,  # This should trigger cleanup
                version=False,
                verbose=False,
            )

        # Verify cleanup was called despite the error
        mock_extractor_instance.cleanup.assert_called_once()

    def test_main_keep_temp_skips_cleanup(
        self,
        tmp_path: Path,
        mock_dependencies: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test that cleanup is skipped when keep_temp is True."""
        mocks = mock_dependencies

        # Set up mocks
        mocks["sanitize"].return_value = tmp_path / "input"
        mocks["ensure_output"].return_value = tmp_path / "output"
        mocks["determine_temp"].return_value = tmp_path / "temp"

        mock_extractor_instance = mocks["extractor"].return_value
        mock_extractor_instance.channels = 2
        mock_extractor_instance.cleanup.return_value = None

        mocks["config_loader"].return_value.load.return_value = ([], [], None)

        # Execute with keep_temp=True
        process(
            input_path=tmp_path / "input",
            output=None,
            bit_depth=BitDepth.INT16,
            temp_dir=None,
            keep_temp=True,  # This should skip cleanup
            version=False,
            verbose=False,
        )

        # Verify cleanup was NOT called
        mock_extractor_instance.cleanup.assert_not_called()


class TestInitConfigCommand:
    """Tests for init_config command function."""

    def test_init_config_default_output(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test successful config generation to default location."""
        output_file = tmp_path / "config.yaml"
        
        # Mock ConfigResolver to return our test path
        mock_resolver = mocker.patch("src.cli.commands.ConfigResolver")
        mock_resolver.get_default_path.return_value = output_file
        
        # Mock ConfigGenerator
        mock_generator_class = mocker.patch("src.config.generator.ConfigGenerator")
        mock_generator_instance = mock_generator_class.return_value
        mock_generator_instance.generate.return_value = None
        
        # Mock Console
        mock_console_class = mocker.patch("src.cli.commands.Console")
        mock_console = mock_console_class.return_value
        
        # Execute command
        init_config(output=None, minimal=False, force=False)
        
        # Verify generator was called
        mock_generator_class.assert_called_once()
        mock_generator_instance.generate.assert_called_once_with(output_file)
        
        # Verify success messages (3 print calls)
        assert mock_console.print.call_count == 3
        first_call = str(mock_console.print.call_args_list[0][0][0])
        assert "Created configuration file" in first_call
        assert str(output_file) in first_call

    def test_init_config_custom_output(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test config generation to custom location."""
        output_file = tmp_path / "custom" / "myconfig.yaml"
        
        # Mock ConfigGenerator
        mock_generator_class = mocker.patch("src.config.generator.ConfigGenerator")
        mock_generator_instance = mock_generator_class.return_value
        
        # Mock Console
        mock_console_class = mocker.patch("src.cli.commands.Console")
        mock_console = mock_console_class.return_value
        
        # Execute command
        init_config(output=output_file, minimal=False, force=False)
        
        # Verify generator was called with custom path
        mock_generator_instance.generate.assert_called_once_with(output_file)
        
        # Verify success message in first print call
        assert mock_console.print.call_count == 3
        first_call = str(mock_console.print.call_args_list[0][0][0])
        assert str(output_file) in first_call

    def test_init_config_minimal_format(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test minimal config generation."""
        output_file = tmp_path / "minimal.yaml"
        
        # Mock ConfigResolver
        mock_resolver = mocker.patch("src.cli.commands.ConfigResolver")
        mock_resolver.get_default_path.return_value = output_file
        
        # Mock ConfigGenerator
        mock_generator_class = mocker.patch("src.config.generator.ConfigGenerator")
        
        # Mock Console
        mocker.patch("src.cli.commands.Console")
        
        # Execute command with minimal flag
        init_config(output=None, minimal=True, force=False)
        
        # Verify generate_minimal was called
        mock_generator_class.generate_minimal.assert_called_once_with(output_file)

    def test_init_config_file_exists_no_force(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test that existing file prevents overwrite without --force."""
        output_file = tmp_path / "existing.yaml"
        output_file.touch()  # Create the file
        
        # Mock ConfigResolver
        mock_resolver = mocker.patch("src.cli.commands.ConfigResolver")
        mock_resolver.get_default_path.return_value = output_file
        
        # Mock Console
        mock_console_class = mocker.patch("src.cli.commands.Console")
        mock_console = mock_console_class.return_value
        
        # Mock typer.Exit
        mock_exit = mocker.patch("src.cli.commands.typer.Exit")
        mock_exit.side_effect = SystemExit(1)
        
        # Execute command - should exit
        with pytest.raises(SystemExit):
            init_config(output=None, minimal=False, force=False)
        
        # Verify error messages
        assert mock_console.print.call_count == 2
        first_call = str(mock_console.print.call_args_list[0][0][0])
        second_call = str(mock_console.print.call_args_list[1][0][0])
        
        assert "already exists" in first_call
        assert "--force" in second_call
        mock_exit.assert_called_once_with(code=1)

    def test_init_config_file_exists_with_force(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test that existing file is overwritten with --force."""
        output_file = tmp_path / "existing.yaml"
        output_file.write_text("old content")
        
        # Mock ConfigResolver
        mock_resolver = mocker.patch("src.cli.commands.ConfigResolver")
        mock_resolver.get_default_path.return_value = output_file
        
        # Mock ConfigGenerator
        mock_generator_class = mocker.patch("src.config.generator.ConfigGenerator")
        mock_generator_instance = mock_generator_class.return_value
        
        # Mock Console
        mocker.patch("src.cli.commands.Console")
        
        # Execute command with force
        init_config(output=None, minimal=False, force=True)
        
        # Verify generator was called (file should be overwritten)
        mock_generator_instance.generate.assert_called_once_with(output_file)

    def test_init_config_os_error_handling(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test handling of OS errors during file writing."""
        output_file = tmp_path / "config.yaml"
        
        # Mock ConfigResolver
        mock_resolver = mocker.patch("src.cli.commands.ConfigResolver")
        mock_resolver.get_default_path.return_value = output_file
        
        # Mock ConfigGenerator to raise OSError
        mock_generator_class = mocker.patch("src.config.generator.ConfigGenerator")
        mock_generator_instance = mock_generator_class.return_value
        mock_generator_instance.generate.side_effect = OSError("Permission denied")
        
        # Mock Console
        mock_console_class = mocker.patch("src.cli.commands.Console")
        mock_console = mock_console_class.return_value
        
        # Mock typer.Exit
        mock_exit = mocker.patch("src.cli.commands.typer.Exit")
        mock_exit.side_effect = SystemExit(1)
        
        # Execute command - should handle error
        with pytest.raises(SystemExit):
            init_config(output=None, minimal=False, force=False)
        
        # Verify error message
        mock_console.print.assert_called_once()
        error_msg = str(mock_console.print.call_args[0][0])
        assert "Failed to write configuration file" in error_msg
        assert "Permission denied" in error_msg
        mock_exit.assert_called_once_with(code=1)


class TestValidateConfigCommand:
    """Tests for validate_config command function."""

    def test_validate_config_success_no_channel_count(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test successful validation without channel count."""
        config_file = tmp_path / "valid.yaml"
        
        # Mock YAMLConfigSource
        mock_source_class = mocker.patch("src.config.yaml_source.YAMLConfigSource")
        mock_source = mock_source_class.return_value
        mock_source.load.return_value = (
            [{"ch": 1, "name": "Channel_1", "action": "BUS"}],
            [{"file_name": "01_Master", "type": "STEREO", "slots": {"LEFT": 1, "RIGHT": 1}}],
            None,  # section_splitting_data
            1,  # schema_version
        )
        
        # Mock ConfigLoader - need to mock both the class and instance
        mock_loader_class = mocker.patch("src.cli.commands.ConfigLoader")
        mock_loader = mock_loader_class.return_value
        # Return actual model instances
        from src.config.models import ChannelConfig, BusConfig, SectionSplittingConfig
        from src.config.enums import BusSlot, ChannelAction, BusType
        mock_loader.load.return_value = (
            [ChannelConfig(ch=1, name="Channel_1", action=ChannelAction.BUS, output_ch=None)],
            [BusConfig(file_name="01_Master", type=BusType.STEREO, slots={BusSlot.LEFT: 1, BusSlot.RIGHT: 1})],
            SectionSplittingConfig(),  # default section_splitting
        )
        
        # Mock Console
        mock_console_class = mocker.patch("src.cli.commands.Console")
        mock_console = mock_console_class.return_value
        
        # Execute command
        validate_config(config_path=config_file, channel_count=None)
        
        # Verify YAMLConfigSource was created
        mock_source_class.assert_called_once_with(config_file)
        mock_source.load.assert_called_once()
        
        # Verify ConfigLoader was created without detected_channel_count
        mock_loader_class.assert_called_once()
        call_kwargs = mock_loader_class.call_args[1]
        assert call_kwargs["detected_channel_count"] is None
        
        # Verify success message
        print_calls = [str(call[0][0]) for call in mock_console.print.call_args_list]
        assert any("Configuration is valid" in call for call in print_calls)

    def test_validate_config_success_with_channel_count(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test successful validation with channel count."""
        config_file = tmp_path / "valid.yaml"
        
        # Mock YAMLConfigSource
        mock_source_class = mocker.patch("src.config.yaml_source.YAMLConfigSource")
        mock_source = mock_source_class.return_value
        # Channels 1-2 are in bus (action=BUS), rest are PROCESS
        channels_data = [{"ch": 1, "name": "Ch_1", "action": "BUS"}, {"ch": 2, "name": "Ch_2", "action": "BUS"}]
        channels_data.extend([{"ch": i, "name": f"Ch_{i}", "action": "PROCESS"} for i in range(3, 9)])
        mock_source.load.return_value = (
            channels_data,
            [{"file_name": "01_Master", "type": "STEREO", "slots": {"LEFT": 1, "RIGHT": 2}}],
            None,  # section_splitting_data
            1,
        )
        
        # Mock ConfigLoader
        mock_loader_class = mocker.patch("src.cli.commands.ConfigLoader")
        mock_loader = mock_loader_class.return_value
        # Return actual model instances
        from src.config.models import ChannelConfig, BusConfig, SectionSplittingConfig
        from src.config.enums import BusSlot, ChannelAction, BusType
        bus_channels = [ChannelConfig(ch=1, name="Ch_1", action=ChannelAction.BUS, output_ch=None), ChannelConfig(ch=2, name="Ch_2", action=ChannelAction.BUS, output_ch=None)]
        process_channels = [ChannelConfig(ch=i, name=f"Ch_{i}", output_ch=None) for i in range(3, 9)]
        mock_loader.load.return_value = (
            bus_channels + process_channels,
            [BusConfig(file_name="01_Master", type=BusType.STEREO, slots={BusSlot.LEFT: 1, BusSlot.RIGHT: 2})],
            SectionSplittingConfig(),  # default section_splitting
        )
        
        # Mock Console
        mock_console_class = mocker.patch("src.cli.commands.Console")
        mock_console = mock_console_class.return_value
        
        # Execute command with channel count
        validate_config(config_path=config_file, channel_count=8)
        
        # Verify ConfigLoader was created with detected_channel_count
        call_kwargs = mock_loader_class.call_args[1]
        assert call_kwargs["detected_channel_count"] == 8
        
        # Verify validation message includes channel count
        print_calls = [str(call[0][0]) for call in mock_console.print.call_args_list]
        assert any("Validated against 8 channels" in call for call in print_calls)

    def test_validate_config_yaml_error(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test handling of YAML syntax errors."""
        config_file = tmp_path / "invalid.yaml"
        
        # Mock YAMLConfigSource to raise YAMLConfigError
        from src.exceptions import YAMLConfigError
        mock_source_class = mocker.patch("src.config.yaml_source.YAMLConfigSource")
        mock_source = mock_source_class.return_value
        mock_source.load.side_effect = YAMLConfigError("Invalid YAML syntax")
        
        # Mock Console
        mock_console_class = mocker.patch("src.cli.commands.Console")
        mock_console = mock_console_class.return_value
        
        # Mock typer.Exit
        mock_exit = mocker.patch("src.cli.commands.typer.Exit")
        mock_exit.side_effect = SystemExit(1)
        
        # Execute command - should handle error
        with pytest.raises(SystemExit):
            validate_config(config_path=config_file, channel_count=None)
        
        # Verify error message
        mock_console.print.assert_called()
        error_msg = str(mock_console.print.call_args[0][0])
        assert "Configuration error" in error_msg
        assert "Invalid YAML syntax" in error_msg
        mock_exit.assert_called_once_with(code=1)

    def test_validate_config_validation_error(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test handling of configuration validation errors."""
        config_file = tmp_path / "invalid.yaml"
        
        # Mock YAMLConfigSource
        mock_source_class = mocker.patch("src.config.yaml_source.YAMLConfigSource")
        mock_source = mock_source_class.return_value
        mock_source.load.return_value = (
            [{"ch": 1, "name": "Channel_1", "action": "PROCESS"}],
            [{"file_name": "01_Master", "type": "STEREO", "slots": {"LEFT": 99, "RIGHT": 99}}],  # Invalid channel reference
            None,  # section_splitting_data
            1,
        )
        
        # Mock ConfigLoader to raise ConfigError
        from src.exceptions import ConfigError
        mock_loader_class = mocker.patch("src.cli.commands.ConfigLoader")
        mock_loader = mock_loader_class.return_value
        mock_loader.load.side_effect = ConfigError("Channel 99 referenced in bus but not defined")
        
        # Mock Console
        mock_console_class = mocker.patch("src.cli.commands.Console")
        mock_console = mock_console_class.return_value
        
        # Mock typer.Exit
        mock_exit = mocker.patch("src.cli.commands.typer.Exit")
        mock_exit.side_effect = SystemExit(1)
        
        # Execute command - should handle error
        with pytest.raises(SystemExit):
            validate_config(config_path=config_file, channel_count=None)
        
        # Verify error message
        error_msg = str(mock_console.print.call_args[0][0])
        assert "Validation error" in error_msg
        assert "Channel 99" in error_msg or "Invalid bus configuration" in error_msg
        mock_exit.assert_called_once_with(code=1)

    def test_validate_config_displays_schema_info(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test that validation displays schema information."""
        config_file = tmp_path / "config.yaml"
        
        # Mock YAMLConfigSource
        mock_source_class = mocker.patch("src.config.yaml_source.YAMLConfigSource")
        mock_source = mock_source_class.return_value
        # Channels 1-4 are in buses (action=BUS), rest are PROCESS
        channels_data = [
            {"ch": 1, "name": "Ch_1", "action": "BUS"}, {"ch": 2, "name": "Ch_2", "action": "BUS"},
            {"ch": 3, "name": "Ch_3", "action": "BUS"}, {"ch": 4, "name": "Ch_4", "action": "BUS"},
        ]
        channels_data.extend([{"ch": i, "name": f"Ch_{i}", "action": "PROCESS"} for i in range(5, 17)])
        mock_source.load.return_value = (
            channels_data,
            [{"file_name": "01_Bus1", "type": "STEREO", "slots": {"LEFT": 1, "RIGHT": 2}}, {"file_name": "02_Bus2", "type": "STEREO", "slots": {"LEFT": 3, "RIGHT": 4}}],
            None,  # section_splitting_data
            2,  # schema_version
        )
        
        # Mock ConfigLoader
        mock_loader_class = mocker.patch("src.cli.commands.ConfigLoader")
        mock_loader = mock_loader_class.return_value
        # Return actual model instances
        from src.config.models import ChannelConfig, BusConfig, SectionSplittingConfig
        from src.config.enums import BusSlot, ChannelAction, BusType
        bus_channels = [ChannelConfig(ch=i, name=f"Ch_{i}", action=ChannelAction.BUS, output_ch=None) for i in range(1, 5)]
        process_channels = [ChannelConfig(ch=i, name=f"Ch_{i}", output_ch=None) for i in range(5, 17)]
        mock_loader.load.return_value = (
            bus_channels + process_channels,
            [BusConfig(file_name="01_Bus1", type=BusType.STEREO, slots={BusSlot.LEFT: 1, BusSlot.RIGHT: 2}), BusConfig(file_name="02_Bus2", type=BusType.STEREO, slots={BusSlot.LEFT: 3, BusSlot.RIGHT: 4})],
            SectionSplittingConfig(),  # default section_splitting
        )
        
        # Mock Console
        mock_console_class = mocker.patch("src.cli.commands.Console")
        mock_console = mock_console_class.return_value
        
        # Execute command
        validate_config(config_path=config_file, channel_count=16)
        
        # Verify schema info was printed
        print_calls = [str(call[0][0]) for call in mock_console.print.call_args_list]
        assert any("Schema version: 2" in call for call in print_calls)
        assert any("Channels defined: 16" in call for call in print_calls)
        assert any("Buses defined: 2" in call for call in print_calls)

"""Unit tests for CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_mock import MockerFixture

from src.cli.commands import version_callback, process
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
        mocks["config_loader"].return_value.load.return_value = ([], [])
        mocks["config_loader"].from_yaml.return_value.load.return_value = ([], [])

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
        mock_config_instance.load.return_value = ([], [])  # empty channels and buses

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

        mocks["config_loader"].return_value.load.return_value = ([], [])

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
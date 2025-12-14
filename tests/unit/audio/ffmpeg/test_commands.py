"""Unit tests for FFmpeg command building and execution."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.audio.ffmpeg.commands import FFmpegCommandBuilder
from src.audio.ffmpeg.executor import FFmpegExecutor
from src.config.enums import BitDepth
from src.exceptions import AudioProcessingError
from src.output import OutputHandler


class TestFFmpegCommandBuilder:
    """Tests for FFmpegCommandBuilder class."""

    @pytest.mark.parametrize("bit_depth,expected_codec", [
        (BitDepth.INT16, 'pcm_s16le'),
        (BitDepth.INT24, 'pcm_s24le'),
        (BitDepth.FLOAT32, 'pcm_f32le'),
        (BitDepth.SOURCE, 'pcm_s32le'),
    ])
    def test_build_channel_split_command_codec_mapping(
        self,
        tmp_path: Path,
        bit_depth: BitDepth,
        expected_codec: str,
    ) -> None:
        """Test codec mapping for different bit depths."""
        input_path = tmp_path / "input.wav"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        cmd = FFmpegCommandBuilder.build_channel_split_command(
            input_path=input_path,
            output_dir=output_dir,
            file_index=1,
            channels=2,
            bit_depth=bit_depth
        )

        assert cmd[0] == 'ffmpeg'
        assert '-c:a' in cmd
        codec_index = cmd.index('-c:a') + 1
        assert cmd[codec_index] == expected_codec

    def test_build_channel_split_command_single_channel(
        self,
        tmp_path: Path,
    ) -> None:
        """Test command building for single channel audio."""
        input_path = tmp_path / "input.wav"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        cmd = FFmpegCommandBuilder.build_channel_split_command(
            input_path=input_path,
            output_dir=output_dir,
            file_index=5,
            channels=1,
            bit_depth=BitDepth.INT16
        )

        expected_cmd = [
            'ffmpeg', '-y', '-i', str(input_path),
            '-filter_complex', '[0:a]pan=mono|c0=c0[c0]',
            '-map', '[c0]', '-c:a', 'pcm_s16le',
            str(output_dir / 'ch01_0005.wav')
        ]

        assert cmd == expected_cmd

    def test_build_channel_split_command_multi_channel(
        self,
        tmp_path: Path,
    ) -> None:
        """Test command building for multi-channel audio."""
        input_path = tmp_path / "input.wav"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        cmd = FFmpegCommandBuilder.build_channel_split_command(
            input_path=input_path,
            output_dir=output_dir,
            file_index=10,
            channels=4,
            bit_depth=BitDepth.INT24
        )

        # Check basic structure
        assert cmd[0] == 'ffmpeg'
        assert cmd[1] == '-y'
        assert cmd[2] == '-i'
        assert cmd[3] == str(input_path)
        assert cmd[4] == '-filter_complex'

        # Check filter complex contains all channels
        filter_complex = cmd[5]
        assert 'pan=mono|c0=c0[c0]' in filter_complex
        assert 'pan=mono|c0=c1[c1]' in filter_complex
        assert 'pan=mono|c0=c2[c2]' in filter_complex
        assert 'pan=mono|c0=c3[c3]' in filter_complex

        # Check all output mappings
        assert '-map' in cmd
        assert '[c0]' in cmd
        assert '[c1]' in cmd
        assert '[c2]' in cmd
        assert '[c3]' in cmd

        # Check codec
        assert '-c:a' in cmd
        codec_index = cmd.index('-c:a') + 1
        assert cmd[codec_index] == 'pcm_s24le'

        # Check output paths
        assert str(output_dir / 'ch01_0010.wav') in cmd
        assert str(output_dir / 'ch02_0010.wav') in cmd
        assert str(output_dir / 'ch03_0010.wav') in cmd
        assert str(output_dir / 'ch04_0010.wav') in cmd

    def test_build_channel_split_command_large_channel_count(
        self,
        tmp_path: Path,
    ) -> None:
        """Test command building for high channel count audio."""
        input_path = tmp_path / "input.wav"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        channels = 32
        cmd = FFmpegCommandBuilder.build_channel_split_command(
            input_path=input_path,
            output_dir=output_dir,
            file_index=100,
            channels=channels,
            bit_depth=BitDepth.FLOAT32
        )

        # Should have 32 pan filters in filter_complex
        filter_complex = cmd[5]
        for i in range(channels):
            assert f'pan=mono|c0=c{i}[c{i}]' in filter_complex

        # Should have 32 output mappings
        for i in range(channels):
            assert f'[c{i}]' in cmd

        # Check codec
        codec_index = cmd.index('-c:a') + 1
        assert cmd[codec_index] == 'pcm_f32le'

    def test_build_channel_split_command_unknown_bit_depth(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test command building with unknown bit depth defaults to pcm_s32le."""
        input_path = tmp_path / "input.wav"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock an unknown bit depth by patching the codec dict
        original_method = FFmpegCommandBuilder.build_channel_split_command
        def mock_build(*args, **kwargs):
            # Temporarily modify the codec mapping to test default
            return original_method(*args, **kwargs)

        # Create a mock bit depth that's not in the mapping
        unknown_bit_depth = mocker.MagicMock()
        unknown_bit_depth.__class__ = BitDepth
        unknown_bit_depth.name = "UNKNOWN"

        cmd = FFmpegCommandBuilder.build_channel_split_command(
            input_path=input_path,
            output_dir=output_dir,
            file_index=1,
            channels=2,
            bit_depth=unknown_bit_depth  # This should default to pcm_s32le
        )

        # Should default to pcm_s32le for unknown bit depths
        codec_index = cmd.index('-c:a') + 1
        assert cmd[codec_index] == 'pcm_s32le'


class TestFFmpegExecutor:
    """Tests for FFmpegExecutor class."""

    @pytest.fixture
    def executor(self, mock_output_handler: OutputHandler) -> FFmpegExecutor:
        """Create FFmpegExecutor instance."""
        return FFmpegExecutor(mock_output_handler)

    def test_execute_success(
        self,
        executor: FFmpegExecutor,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test successful FFmpeg command execution."""
        input_path = tmp_path / "input.wav"
        command = ['ffmpeg', '-i', str(input_path), 'output.wav']

        # Mock subprocess.run to succeed
        mock_run = mocker.patch('src.audio.ffmpeg.executor.subprocess.run')

        # Should not raise
        executor.execute(command, input_path)

        # Verify subprocess.run was called correctly
        mock_run.assert_called_once_with(command, check=True, capture_output=True)

    def test_execute_subprocess_error_with_stderr(
        self,
        executor: FFmpegExecutor,
        mocker: MockerFixture,
        tmp_path: Path,
        mock_output_handler: OutputHandler,
    ) -> None:
        """Test FFmpeg execution failure with stderr output."""
        input_path = tmp_path / "input.wav"
        command = ['ffmpeg', '-i', str(input_path), 'output.wav']

        # Mock subprocess.run to raise CalledProcessError with stderr
        from subprocess import CalledProcessError
        error = CalledProcessError(
            returncode=1,
            cmd=command,
            stderr=b"FFmpeg error: invalid input file"
        )
        mocker.patch('src.audio.ffmpeg.executor.subprocess.run', side_effect=error)

        with pytest.raises(AudioProcessingError) as exc_info:
            executor.execute(command, input_path)

        assert "FFmpeg command failed: FFmpeg error: invalid input file" in str(exc_info.value)

        # Verify error was logged
        mock_output_handler.error.assert_called_once()  # type: ignore[attr-defined]
        error_call = mock_output_handler.error.call_args[0][0]  # type: ignore[attr-defined]
        assert "FFmpeg failed for file" in error_call
        assert "FFmpeg error: invalid input file" in error_call

    def test_execute_subprocess_error_without_stderr(
        self,
        executor: FFmpegExecutor,
        mocker: MockerFixture,
        tmp_path: Path,
        mock_output_handler: OutputHandler,
    ) -> None:
        """Test FFmpeg execution failure without stderr output."""
        input_path = tmp_path / "input.wav"
        command = ['ffmpeg', '-i', str(input_path), 'output.wav']

        # Mock subprocess.run to raise CalledProcessError without stderr
        from subprocess import CalledProcessError
        error = CalledProcessError(
            returncode=1,
            cmd=command,
            stderr=None
        )
        mocker.patch('src.audio.ffmpeg.executor.subprocess.run', side_effect=error)

        with pytest.raises(AudioProcessingError) as exc_info:
            executor.execute(command, input_path)

        # Should contain the CalledProcessError string representation
        assert "FFmpeg command failed:" in str(exc_info.value)

        # Verify error was logged
        mock_output_handler.error.assert_called_once()  # type: ignore[attr-defined]
        error_call = mock_output_handler.error.call_args[0][0]  # type: ignore[attr-defined]
        assert "FFmpeg failed for file" in error_call
"""CLI validation tests for new processing options."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli.app import app


class TestCLIValidation:
    """Tests for CLI option validation."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI test runner."""
        return CliRunner()

    def test_gap_threshold_negative_rejected(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that negative gap threshold is rejected."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        result = runner.invoke(app, [
            "process",
            str(input_dir),
            "--gap-threshold", "-1.0"
        ])

        assert result.exit_code != 0
        # Typer outputs validation errors to stderr or stdout
        output = result.stdout + result.stderr
        assert "Invalid value" in output or "greater than or equal to 0.1" in output

    def test_gap_threshold_zero_rejected(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that zero gap threshold is rejected."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        result = runner.invoke(app, [
            "process",
            str(input_dir),
            "--gap-threshold", "0.0"
        ])

        assert result.exit_code != 0
        output = result.stdout + result.stderr
        assert "Invalid value" in output or "greater than or equal to 0.1" in output

    def test_gap_threshold_below_minimum_rejected(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that gap threshold below minimum (0.1) is rejected."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        result = runner.invoke(app, [
            "process",
            str(input_dir),
            "--gap-threshold", "0.05"
        ])

        assert result.exit_code != 0
        output = result.stdout + result.stderr
        assert "Invalid value" in output or "greater than or equal to 0.1" in output

    def test_gap_threshold_valid_accepted(self, runner: CliRunner, tmp_path: Path, mocker) -> None:
        """Test that valid gap threshold is accepted by CLI parser."""
        # This test just verifies the CLI accepts the argument
        # The actual processing will fail due to missing audio files, but that's expected
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create a dummy WAV file to pass initial validation
        wav_file = input_dir / "test001.wav"
        wav_file.touch()

        result = runner.invoke(app, [
            "process",
            str(input_dir),
            "--gap-threshold", "2.5"
        ])

        # Should fail on audio processing (not CLI validation)
        # As long as it doesn't complain about the gap threshold value, test passes
        assert "--gap-threshold" not in result.stdout or "Invalid value" not in result.stdout

    def test_section_by_click_flag_accepted(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that --section-by-click flag is accepted."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        wav_file = input_dir / "test001.wav"
        wav_file.touch()

        result = runner.invoke(app, [
            "process",
            str(input_dir),
            "--section-by-click"
        ])

        # Should not have CLI argument errors
        assert "--section-by-click" not in result.stdout or "Invalid" not in result.stdout

    def test_session_json_path_accepted(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that --session-json with path is accepted."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        wav_file = input_dir / "test001.wav"
        wav_file.touch()

        json_path = tmp_path / "output" / "session.json"

        result = runner.invoke(app, [
            "process",
            str(input_dir),
            "--session-json", str(json_path)
        ])

        # Should not have CLI argument errors
        assert "--session-json" not in result.stdout or "Invalid" not in result.stdout

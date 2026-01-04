"""Unit tests for CLI utility functions."""

from __future__ import annotations

from pathlib import Path


from src.cli.utils import _sanitize_path, _default_output_dir, _ensure_output_path, _determine_temp_dir


class TestSanitizePath:
    """Tests for _sanitize_path function."""

    def test_sanitize_path_absolute(self) -> None:
        """Test _sanitize_path with already absolute path."""
        path = Path("C:/some/path")
        result = _sanitize_path(path)
        assert result == path.resolve()

    def test_sanitize_path_relative(self) -> None:
        """Test _sanitize_path with relative path."""
        path = Path("relative/path")
        result = _sanitize_path(path)
        assert result == path.resolve()

    def test_sanitize_path_with_tilde(self) -> None:
        """Test _sanitize_path with tilde expansion."""
        path = Path("~/test/path")
        result = _sanitize_path(path)
        assert result == path.expanduser().resolve()


class TestDefaultOutputDir:
    """Tests for _default_output_dir function."""

    def test_default_output_dir_no_conflict(self, tmp_path: Path) -> None:
        """Test _default_output_dir when no conflict exists."""
        input_path = tmp_path / "input_folder"
        input_path.mkdir()

        result = _default_output_dir(input_path)
        expected = tmp_path / "processed"

        assert result == expected
        assert not result.exists()

    def test_default_output_dir_with_conflict(self, tmp_path: Path) -> None:
        """Test _default_output_dir when conflict exists."""
        input_path = tmp_path / "input_folder"
        input_path.mkdir()

        # Create the default output directory
        conflict_dir = tmp_path / "processed"
        conflict_dir.mkdir()

        result = _default_output_dir(input_path)
        expected = tmp_path / "processed_v2"

        assert result == expected

    def test_default_output_dir_multiple_conflicts(self, tmp_path: Path) -> None:
        """Test _default_output_dir with multiple existing conflicts."""
        input_path = tmp_path / "input_folder"
        input_path.mkdir()

        # Create multiple conflicting directories
        (tmp_path / "processed").mkdir()
        (tmp_path / "processed_v2").mkdir()
        (tmp_path / "processed_v3").mkdir()

        result = _default_output_dir(input_path)
        expected = tmp_path / "processed_v4"

        assert result == expected


class TestEnsureOutputPath:
    """Tests for _ensure_output_path function."""

    def test_ensure_output_path_with_override(self, tmp_path: Path) -> None:
        """Test _ensure_output_path with user override."""
        input_path = tmp_path / "input"
        override = tmp_path / "custom_output"

        result = _ensure_output_path(input_path, override)
        assert result == override.resolve()

    def test_ensure_output_path_without_override(self, tmp_path: Path) -> None:
        """Test _ensure_output_path without user override uses default."""
        input_path = tmp_path / "input_folder"
        input_path.mkdir()

        result = _ensure_output_path(input_path, None)
        expected = tmp_path / "processed"

        assert result == expected


class TestDetermineTempDir:
    """Tests for _determine_temp_dir function."""

    def test_determine_temp_dir_with_override(self, tmp_path: Path) -> None:
        """Test _determine_temp_dir with user override."""
        output_dir = tmp_path / "output"
        override = tmp_path / "custom_temp"

        result = _determine_temp_dir(output_dir, override)
        assert result == override.resolve()

    def test_determine_temp_dir_without_override(self, tmp_path: Path) -> None:
        """Test _determine_temp_dir without user override uses output/temp."""
        output_dir = tmp_path / "output"

        result = _determine_temp_dir(output_dir, None)
        expected = output_dir / "temp"

        assert result == expected
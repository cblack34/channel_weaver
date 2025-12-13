"""Basic test to verify test infrastructure is working."""

from __future__ import annotations

from pathlib import Path



class TestBasicInfrastructure:
    """Basic tests to verify pytest setup and fixtures work."""

    def test_tmp_input_dir_fixture(self, tmp_input_dir: Path) -> None:
        """Test that tmp_input_dir fixture creates a directory."""
        assert tmp_input_dir.exists()
        assert tmp_input_dir.is_dir()
        assert tmp_input_dir.name == "input"

    def test_tmp_output_dir_fixture(self, tmp_output_dir: Path) -> None:
        """Test that tmp_output_dir fixture creates a directory."""
        assert tmp_output_dir.exists()
        assert tmp_output_dir.is_dir()
        assert tmp_output_dir.name == "output"

    def test_tmp_temp_dir_fixture(self, tmp_temp_dir: Path) -> None:
        """Test that tmp_temp_dir fixture creates a directory."""
        assert tmp_temp_dir.exists()
        assert tmp_temp_dir.is_dir()
        assert tmp_temp_dir.name == "temp"

    def test_mock_console_fixture(self, mock_console) -> None:
        """Test that mock_console fixture provides expected methods."""
        assert hasattr(mock_console, "print")
        assert hasattr(mock_console, "log")
        assert hasattr(mock_console, "status")

    def test_mock_output_handler_fixture(self, mock_output_handler) -> None:
        """Test that mock_output_handler fixture provides expected methods."""
        assert hasattr(mock_output_handler, "info")
        assert hasattr(mock_output_handler, "warning")
        assert hasattr(mock_output_handler, "error")
        assert hasattr(mock_output_handler, "success")

    def test_directories_are_separate(self, tmp_input_dir: Path, tmp_output_dir: Path, tmp_temp_dir: Path) -> None:
        """Test that all temp directories are separate."""
        dirs = [tmp_input_dir, tmp_output_dir, tmp_temp_dir]
        for i, dir1 in enumerate(dirs):
            for j, dir2 in enumerate(dirs):
                if i != j:
                    assert dir1 != dir2, f"Directories {dir1.name} and {dir2.name} should be different"
"""Unit test shared fixtures.

Fixtures here are available to all unit tests but not integration tests.
Focus on lightweight mocks and fast execution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


# =============================================================================
# Automatic Markers
# =============================================================================

def pytest_collection_modifyitems(items):
    """Automatically mark all tests in unit/ directory with @pytest.mark.unit."""
    for item in items:
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)


# =============================================================================
# Sample Data Factories
# =============================================================================

@pytest.fixture
def channel_data_factory():
    """Factory fixture for creating channel configuration dictionaries.

    Returns:
        Callable that creates channel data dictionaries with sensible defaults.

    Example:
        >>> data = channel_data_factory(ch=1, name="Kick")
        >>> assert data == {"ch": 1, "name": "Kick", "action": "PROCESS"}
    """
    def _create(
        ch: int = 1,
        name: str = "Test Channel",
        action: str = "PROCESS",
        output_ch: int | None = None,
    ) -> dict[str, Any]:
        data = {"ch": ch, "name": name, "action": action}
        if output_ch is not None:
            data["output_ch"] = output_ch
        return data

    return _create


@pytest.fixture
def bus_data_factory():
    """Factory fixture for creating bus configuration dictionaries.

    Returns:
        Callable that creates bus data dictionaries with sensible defaults.
    """
    def _create(
        file_name: str = "test_bus",
        bus_type: str = "STEREO",
        left_ch: int = 1,
        right_ch: int = 2,
    ) -> dict[str, Any]:
        return {
            "file_name": file_name,
            "type": bus_type,
            "slots": {"LEFT": left_ch, "RIGHT": right_ch},
        }

    return _create


# =============================================================================
# Mock WAV File Creation
# =============================================================================

@pytest.fixture
def create_mock_wav_file(tmp_path: Path):
    """Factory fixture for creating mock WAV file paths.

    Creates empty files that simulate WAV files without actual audio data.
    Useful for testing file discovery and path handling.

    Returns:
        Callable that creates a mock WAV file and returns its path.
    """
    def _create(filename: str = "00000001.WAV", size: int = 1024) -> Path:
        file_path = tmp_path / filename
        # Create a file with specified size (simulating audio data)
        file_path.write_bytes(b"\x00" * size)
        return file_path

    return _create
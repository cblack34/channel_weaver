"""Root-level pytest configuration and shared fixtures.

This module provides fixtures that are universally applicable across
all test modules. Fixtures here should be:
- Stateless or session-scoped
- Generic enough for reuse across different test categories
- Well-documented with clear purpose
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Generator

import pytest
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest


# =============================================================================
# Path Fixtures
# =============================================================================

@pytest.fixture
def tmp_input_dir(tmp_path: Path) -> Path:
    """Create a temporary input directory for test files.

    Returns:
        Path to a clean temporary directory for input files.
    """
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    return input_dir


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for processed files.

    Returns:
        Path to a clean temporary directory for output files.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def tmp_temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for intermediate processing files.

    Returns:
        Path to a clean temporary directory for temp files.
    """
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


# =============================================================================
# Mock Console Fixtures
# =============================================================================

@pytest.fixture
def mock_console(mocker: MockerFixture):
    """Create a mock Rich Console for output testing.

    Returns:
        Mock object that mimics rich.console.Console interface.
    """
    return mocker.MagicMock(spec_set=["print", "log", "status"])


# =============================================================================
# Output Handler Fixtures
# =============================================================================

@pytest.fixture
def mock_output_handler(mocker: MockerFixture):
    """Create a mock OutputHandler for dependency injection.

    This mock implements the OutputHandler protocol with stub methods
    for info, warning, error, and success messages.

    Returns:
        Mock object implementing OutputHandler protocol.
    """
    handler = mocker.MagicMock()
    handler.info = mocker.MagicMock()
    handler.warning = mocker.MagicMock()
    handler.error = mocker.MagicMock()
    handler.success = mocker.MagicMock()
    return handler


# =============================================================================
# Configuration Markers
# =============================================================================

def pytest_configure(config):
    """Register custom markers for test categorization."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "ffmpeg: Tests involving FFmpeg")
    config.addinivalue_line("markers", "pydantic: Tests for Pydantic validation")
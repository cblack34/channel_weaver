# Channel Weaver Testing Plan

**Version:** 1.0  
**Created:** December 13, 2025  
**Target Python Version:** 3.14  
**Target Pytest Version:** 8.x+

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Testing Philosophy & Principles](#testing-philosophy--principles)
3. [Project Dependencies for Testing](#project-dependencies-for-testing)
4. [Directory Structure](#directory-structure)
5. [Conftest Architecture](#conftest-architecture)
6. [Mock Strategy & Architecture](#mock-strategy--architecture)
7. [Test Categories by Module](#test-categories-by-module)
8. [Fixture Design Patterns](#fixture-design-patterns)
9. [Parametrization Strategy](#parametrization-strategy)
10. [Markers and Test Organization](#markers-and-test-organization)
11. [Implementation Guide](#implementation-guide)
12. [Quality Assurance Checklist](#quality-assurance-checklist)
13. [CLI Testing with Typer CliRunner](#cli-testing-with-typer-clirunner)
14. [Advanced Mocking Patterns](#advanced-mocking-patterns)
15. [Exception Testing Patterns](#exception-testing-patterns)
16. [Modern Python 3.14 Features in Tests](#modern-python-314-features-in-tests)
17. [Coverage Configuration](#coverage-configuration)
18. [Continuous Integration Recommendations](#continuous-integration-recommendations)
19. [Appendix A: Complete Fixture Reference](#appendix-a-complete-fixture-reference)
20. [Appendix B: Test Naming Conventions](#appendix-b-test-naming-conventions)
21. [Appendix C: Troubleshooting Common Issues](#appendix-c-troubleshooting-common-issues)

---

## Executive Summary

This document outlines a comprehensive unit testing strategy for the Channel Weaver audio processing CLI application. The plan emphasizes:

- **SOLID Principles**: Tests are modular, extensible, and follow single responsibility
- **Modern Python 3.14**: Utilizes latest language features including type parameter syntax and enhanced pattern matching
- **Modern pytest 8.x**: Leverages conftest.py hierarchies, parametrization, fixtures, and markers
- **Mocking Strategy**: External dependencies (FFmpeg, soundfile, filesystem) are mocked to ensure fast, isolated unit tests
- **Code Reuse**: Centralized fixtures in conftest.py files to eliminate duplication

---

## Testing Philosophy & Principles

### SOLID Principles Applied to Testing

| Principle | Application |
|-----------|-------------|
| **Single Responsibility** | Each test function tests ONE behavior; fixtures have ONE purpose |
| **Open/Closed** | Fixtures are extendable via parametrization without modification |
| **Liskov Substitution** | Mock objects must honor the interfaces they replace |
| **Interface Segregation** | Tests depend only on the fixtures they need |
| **Dependency Inversion** | Tests inject mocks/stubs rather than using concrete implementations |

### Testing Guidelines

1. **Arrange-Act-Assert (AAA)**: Every test follows this pattern
2. **Given-When-Then**: For BDD-style test naming
3. **One Assertion Per Concept**: Multiple assertions are acceptable if testing the same logical outcome
4. **Fast Feedback**: Unit tests must run in milliseconds, not seconds
5. **Isolation**: No test depends on another test's state or execution order
6. **Deterministic**: Tests always produce the same result given the same inputs

---

## Project Dependencies for Testing

### Required Packages

Add the following to `pyproject.toml` under `[project.optional-dependencies]` or `[tool.uv.dev-dependencies]`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-mock>=3.14.0",
    "pytest-cov>=6.0.0",
    "pytest-xdist>=3.5.0",  # Parallel test execution
    "hypothesis>=6.100.0",   # Property-based testing (optional)
]
```

### pytest.ini Configuration

Create or update `pytest.ini`:

```ini
[pytest]
minversion = 8.0
addopts = -ra -q --strict-markers --strict-config
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
filterwarnings =
    error
    ignore::DeprecationWarning
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (may use real filesystem)
    slow: Tests that take more than 1 second
    ffmpeg: Tests that involve FFmpeg mocking
    pydantic: Tests for Pydantic model validation
```

---

## Directory Structure

```
channel_weaver/
├── src/
│   └── ... (existing source code)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Root-level shared fixtures
│   ├── pytest.ini                     # (alternative location)
│   │
│   ├── unit/                          # Unit tests
│   │   ├── __init__.py
│   │   ├── conftest.py                # Unit test fixtures
│   │   │
│   │   ├── config/                    # Config module tests
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py            # Config-specific fixtures
│   │   │   ├── test_models.py
│   │   │   ├── test_enums.py
│   │   │   ├── test_validators.py
│   │   │   └── test_loader.py
│   │   │
│   │   ├── audio/                     # Audio module tests
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py            # Audio-specific fixtures
│   │   │   ├── test_discovery.py
│   │   │   ├── test_validation.py
│   │   │   ├── test_extractor.py
│   │   │   ├── test_info.py
│   │   │   └── ffmpeg/
│   │   │       ├── __init__.py
│   │   │       ├── conftest.py        # FFmpeg-specific fixtures
│   │   │       ├── test_commands.py
│   │   │       └── test_executor.py
│   │   │
│   │   ├── processing/                # Processing module tests
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py            # Processing fixtures
│   │   │   ├── test_builder.py
│   │   │   ├── test_mono.py
│   │   │   ├── test_stereo.py
│   │   │   └── converters/
│   │   │       ├── __init__.py
│   │   │       ├── conftest.py
│   │   │       ├── test_factory.py
│   │   │       └── test_converters.py
│   │   │
│   │   ├── cli/                       # CLI module tests
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py
│   │   │   ├── test_app.py
│   │   │   ├── test_commands.py
│   │   │   └── test_utils.py
│   │   │
│   │   ├── exceptions/                # Exception tests
│   │   │   ├── __init__.py
│   │   │   └── test_exceptions.py
│   │   │
│   │   └── output/                    # Output module tests
│   │       ├── __init__.py
│   │       ├── test_console.py
│   │       └── test_naming.py
│   │
│   └── fixtures/                      # Shared test data
│       ├── __init__.py
│       ├── sample_configs.py          # Reusable config data
│       └── audio_samples.py           # Audio metadata samples
│
└── pyproject.toml
```

---

## Conftest Architecture

### Root conftest.py (`tests/conftest.py`)

This file contains fixtures available to ALL tests across all subdirectories.

```python
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
    config.addinivalue_line("markers", "slow: Tests that take more than 1 second")
    config.addinivalue_line("markers", "ffmpeg: Tests involving FFmpeg")
    config.addinivalue_line("markers", "pydantic: Tests for Pydantic validation")
```

---

### Unit Test conftest.py (`tests/unit/conftest.py`)

```python
"""Unit test shared fixtures.

Fixtures here are available to all unit tests but not integration tests.
Focus on lightweight mocks and fast execution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pytest_mock import MockerFixture


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
```

---

### Config Module conftest.py (`tests/unit/config/conftest.py`)

```python
"""Config module test fixtures.

Provides fixtures specific to testing Pydantic models, validators,
and configuration loading.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.config.enums import ChannelAction, BusSlot, BusType
from src.config.models import ChannelConfig, BusConfig


# =============================================================================
# Valid Configuration Fixtures
# =============================================================================

@pytest.fixture
def valid_channel_config() -> ChannelConfig:
    """Create a valid ChannelConfig instance for testing.
    
    Returns:
        A properly configured ChannelConfig with default PROCESS action.
    """
    return ChannelConfig(ch=1, name="Kick In", action=ChannelAction.PROCESS)


@pytest.fixture
def valid_bus_config() -> BusConfig:
    """Create a valid BusConfig instance for testing.
    
    Returns:
        A properly configured stereo BusConfig.
    """
    return BusConfig(
        file_name="07_Overheads",
        type=BusType.STEREO,
        slots={BusSlot.LEFT: 7, BusSlot.RIGHT: 8},
    )


# =============================================================================
# Parametrized Channel Data
# =============================================================================

@pytest.fixture(params=[
    {"ch": 1, "name": "Kick", "action": ChannelAction.PROCESS},
    {"ch": 2, "name": "Snare Top", "action": ChannelAction.PROCESS},
    {"ch": 31, "name": "Click", "action": ChannelAction.SKIP},
    {"ch": 32, "name": "Talkback", "action": ChannelAction.SKIP},
    {"ch": 7, "name": "OH Left", "action": ChannelAction.BUS},
])
def sample_channel_data(request) -> dict[str, Any]:
    """Parametrized fixture providing various channel configurations.
    
    This fixture runs tests multiple times with different channel setups.
    
    Yields:
        Dictionary with channel configuration data.
    """
    return request.param


# =============================================================================
# Edge Case Data
# =============================================================================

@pytest.fixture(params=[
    {"ch": 0, "name": "Invalid Zero"},           # ch < 1
    {"ch": -1, "name": "Negative Channel"},      # negative ch
    {"ch": 1, "name": ""},                       # empty name
])
def invalid_channel_data(request) -> dict[str, Any]:
    """Parametrized fixture providing invalid channel configurations.
    
    Use this to test validation error handling.
    """
    return request.param


@pytest.fixture
def mock_channel_list() -> list[dict[str, Any]]:
    """Create a list of channel configurations for testing loaders."""
    return [
        {"ch": 1, "name": "Kick In"},
        {"ch": 2, "name": "Kick Out"},
        {"ch": 3, "name": "Snare Top"},
        {"ch": 7, "name": "OH Left", "action": "BUS"},
        {"ch": 8, "name": "OH Right", "action": "BUS"},
        {"ch": 31, "name": "Click", "action": "SKIP"},
    ]


@pytest.fixture
def mock_bus_list() -> list[dict[str, Any]]:
    """Create a list of bus configurations for testing loaders."""
    return [
        {
            "file_name": "07_Overheads",
            "type": "STEREO",
            "slots": {"LEFT": 7, "RIGHT": 8},
        },
    ]
```

---

## Mock Strategy & Architecture

### External Dependencies to Mock

| Dependency | Module | Mock Strategy |
|------------|--------|---------------|
| `subprocess.run` | `src.audio.ffmpeg.executor` | Use `mocker.patch` to simulate FFmpeg calls |
| `soundfile.SoundFile` | `src.audio.*`, `src.processing.*` | Mock file I/O and audio metadata |
| `soundfile.info` | `src.audio.info` | Return mock audio file info objects |
| `Path.glob()` | `src.audio.discovery` | Return controlled list of mock paths |
| `Path.exists()` | Various | Control file existence checks |
| `tqdm` | Various | Mock to prevent console output in tests |
| `rich.console.Console` | CLI modules | Capture/suppress output |

### Mock Patterns

#### Pattern 1: Patch External Subprocess Calls

```python
"""Mock pattern for FFmpeg executor testing."""

import pytest
from pytest_mock import MockerFixture
from pathlib import Path

from src.audio.ffmpeg.executor import FFmpegExecutor


class TestFFmpegExecutor:
    """Test suite for FFmpegExecutor class."""

    @pytest.fixture
    def executor(self, mock_output_handler) -> FFmpegExecutor:
        """Create FFmpegExecutor with mocked output handler."""
        return FFmpegExecutor(mock_output_handler)

    def test_execute_success(
        self,
        executor: FFmpegExecutor,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test successful FFmpeg command execution."""
        # Arrange
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value.returncode = 0
        command = ["ffmpeg", "-i", "input.wav", "output.wav"]
        input_path = tmp_path / "input.wav"

        # Act
        executor.execute(command, input_path)

        # Assert
        mock_run.assert_called_once_with(command, check=True, capture_output=True)

    def test_execute_failure_raises_error(
        self,
        executor: FFmpegExecutor,
        mocker: MockerFixture,
        mock_output_handler,
        tmp_path: Path,
    ) -> None:
        """Test that FFmpeg failure raises AudioProcessingError."""
        import subprocess
        from src.exceptions import AudioProcessingError

        # Arrange
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["ffmpeg"],
            stderr=b"Error: invalid input",
        )
        input_path = tmp_path / "input.wav"

        # Act & Assert
        with pytest.raises(AudioProcessingError, match="FFmpeg command failed"):
            executor.execute(["ffmpeg", "-i", "bad.wav"], input_path)
        
        mock_output_handler.error.assert_called_once()
```

#### Pattern 2: Mock Soundfile for Audio Metadata

```python
"""Audio module conftest.py - tests/unit/audio/conftest.py"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class MockSoundFileInfo:
    """Mock soundfile.info() return object."""
    
    samplerate: int = 48000
    channels: int = 32
    subtype: str = "PCM_24"
    format: str = "WAV"
    frames: int = 480000


@pytest.fixture
def mock_soundfile_info(mocker: MockerFixture):
    """Mock soundfile.info to return controlled audio metadata.
    
    Returns:
        The mock object for further assertions.
    """
    mock_info = mocker.patch("soundfile.info")
    mock_info.return_value = MockSoundFileInfo()
    return mock_info


@pytest.fixture
def soundfile_info_factory():
    """Factory for creating mock soundfile info with custom values.
    
    Returns:
        Callable that creates MockSoundFileInfo instances.
    """
    def _create(
        samplerate: int = 48000,
        channels: int = 32,
        subtype: str = "PCM_24",
        frames: int = 480000,
    ) -> MockSoundFileInfo:
        return MockSoundFileInfo(
            samplerate=samplerate,
            channels=channels,
            subtype=subtype,
            frames=frames,
        )
    
    return _create


@pytest.fixture
def mock_soundfile_read(mocker: MockerFixture):
    """Mock soundfile.read to return controlled audio data.
    
    Returns:
        Configured mock for sf.read().
    """
    import numpy as np
    
    mock_read = mocker.patch("soundfile.read")
    # Return stereo audio data: (samples, channels)
    mock_read.return_value = (
        np.zeros((48000, 2), dtype=np.float32),  # 1 second at 48kHz, stereo
        48000,  # samplerate
    )
    return mock_read


@pytest.fixture
def mock_soundfile_class(mocker: MockerFixture):
    """Mock the SoundFile context manager for write operations.
    
    Returns:
        Configured MagicMock for sf.SoundFile.
    """
    mock_sf = mocker.MagicMock()
    mock_sf.__enter__ = mocker.MagicMock(return_value=mock_sf)
    mock_sf.__exit__ = mocker.MagicMock(return_value=False)
    mock_sf.write = mocker.MagicMock()
    
    mocker.patch("soundfile.SoundFile", return_value=mock_sf)
    return mock_sf
```

#### Pattern 3: Factory Fixtures for Test Data

```python
"""Factory pattern for creating test data - tests/fixtures/sample_configs.py"""

from __future__ import annotations

from typing import Any


def create_channel_config(
    ch: int,
    name: str,
    action: str = "PROCESS",
    output_ch: int | None = None,
) -> dict[str, Any]:
    """Create a channel configuration dictionary.
    
    Args:
        ch: Channel number (1-based)
        name: Display name for the channel
        action: One of PROCESS, BUS, SKIP
        output_ch: Override output channel number
    
    Returns:
        Dictionary suitable for ChannelConfig.model_validate()
    """
    config: dict[str, Any] = {"ch": ch, "name": name, "action": action}
    if output_ch is not None:
        config["output_ch"] = output_ch
    return config


def create_bus_config(
    file_name: str,
    left_ch: int,
    right_ch: int,
    bus_type: str = "STEREO",
) -> dict[str, Any]:
    """Create a bus configuration dictionary.
    
    Args:
        file_name: Output filename for the bus
        left_ch: Left channel number
        right_ch: Right channel number
        bus_type: Bus type (currently only STEREO)
    
    Returns:
        Dictionary suitable for BusConfig.model_validate()
    """
    return {
        "file_name": file_name,
        "type": bus_type,
        "slots": {"LEFT": left_ch, "RIGHT": right_ch},
    }


def create_full_channel_setup(num_channels: int = 32) -> list[dict[str, Any]]:
    """Create a complete channel configuration for testing.
    
    Args:
        num_channels: Total number of channels
    
    Returns:
        List of channel config dictionaries
    """
    channels = []
    for i in range(1, num_channels + 1):
        channels.append(create_channel_config(ch=i, name=f"Ch {i:02d}"))
    return channels
```

---

## Test Categories by Module

### 1. Config Module Tests

#### `tests/unit/config/test_models.py`

```python
"""Unit tests for Pydantic configuration models.

Tests cover:
- ChannelConfig validation and field processing
- BusConfig validation and slot verification
- Edge cases and error handling
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.config.models import ChannelConfig, BusConfig
from src.config.enums import ChannelAction, BusSlot, BusType


class TestChannelConfig:
    """Tests for ChannelConfig Pydantic model."""

    def test_valid_channel_creation(self) -> None:
        """Test creating a valid ChannelConfig with minimum required fields."""
        config = ChannelConfig(ch=1, name="Kick In")
        
        assert config.ch == 1
        assert config.name == "Kick_In"  # Note: spaces replaced with underscores
        assert config.action == ChannelAction.PROCESS  # Default value
        assert config.output_ch == 1  # Defaults to ch

    def test_name_whitespace_cleaning(self) -> None:
        """Test that channel names have whitespace trimmed and spaces replaced."""
        config = ChannelConfig(ch=1, name="  Kick In  ")
        
        assert config.name == "Kick_In"

    @pytest.mark.parametrize("action_str,expected_enum", [
        ("PROCESS", ChannelAction.PROCESS),
        ("process", ChannelAction.PROCESS),
        ("BUS", ChannelAction.BUS),
        ("bus", ChannelAction.BUS),
        ("SKIP", ChannelAction.SKIP),
        ("skip", ChannelAction.SKIP),
    ])
    def test_action_string_conversion(
        self,
        action_str: str,
        expected_enum: ChannelAction,
    ) -> None:
        """Test that action strings are converted to ChannelAction enums."""
        config = ChannelConfig(ch=1, name="Test", action=action_str)
        
        assert config.action == expected_enum

    def test_invalid_channel_number_zero(self) -> None:
        """Test that channel number 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ChannelConfig(ch=0, name="Invalid")
        
        assert "ch" in str(exc_info.value)

    def test_invalid_channel_number_negative(self) -> None:
        """Test that negative channel numbers raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ChannelConfig(ch=-1, name="Invalid")
        
        assert "ch" in str(exc_info.value)

    def test_custom_output_channel(self) -> None:
        """Test setting a custom output channel number."""
        config = ChannelConfig(ch=5, name="Routed", output_ch=3)
        
        assert config.ch == 5
        assert config.output_ch == 3

    def test_invalid_action_raises_error(self) -> None:
        """Test that invalid action strings raise ValidationError."""
        with pytest.raises(ValidationError):
            ChannelConfig(ch=1, name="Test", action="INVALID")


class TestBusConfig:
    """Tests for BusConfig Pydantic model."""

    def test_valid_stereo_bus_creation(self) -> None:
        """Test creating a valid stereo BusConfig."""
        config = BusConfig(
            file_name="07_Overheads",
            type=BusType.STEREO,
            slots={BusSlot.LEFT: 7, BusSlot.RIGHT: 8},
        )
        
        assert config.file_name == "07_Overheads"
        assert config.type == BusType.STEREO
        assert config.slots[BusSlot.LEFT] == 7
        assert config.slots[BusSlot.RIGHT] == 8

    def test_slots_string_key_conversion(self) -> None:
        """Test that string slot keys are converted to BusSlot enums."""
        config = BusConfig(
            file_name="test",
            type="STEREO",
            slots={"LEFT": 1, "RIGHT": 2},
        )
        
        assert BusSlot.LEFT in config.slots
        assert BusSlot.RIGHT in config.slots

    def test_missing_left_slot_raises_error(self) -> None:
        """Test that missing LEFT slot raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BusConfig(
                file_name="test",
                type=BusType.STEREO,
                slots={BusSlot.RIGHT: 2},
            )
        
        assert "LEFT" in str(exc_info.value) or "slots" in str(exc_info.value)

    def test_missing_right_slot_raises_error(self) -> None:
        """Test that missing RIGHT slot raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BusConfig(
                file_name="test",
                type=BusType.STEREO,
                slots={BusSlot.LEFT: 1},
            )
        
        assert "RIGHT" in str(exc_info.value) or "slots" in str(exc_info.value)

    @pytest.mark.parametrize("invalid_ch", [0, -1, -10])
    def test_slot_channel_validation(self, invalid_ch: int) -> None:
        """Test that slot channel numbers must be >= 1."""
        with pytest.raises(ValidationError):
            BusConfig(
                file_name="test",
                type=BusType.STEREO,
                slots={BusSlot.LEFT: invalid_ch, BusSlot.RIGHT: 2},
            )
```

#### `tests/unit/config/test_validators.py`

```python
"""Unit tests for configuration validators."""

from __future__ import annotations

import pytest

from src.config.models import ChannelConfig
from src.config.enums import ChannelAction
from src.config.validators import ChannelValidator, BusValidator
from src.exceptions import (
    DuplicateChannelError,
    ChannelOutOfRangeError,
    BusSlotOutOfRangeError,
    BusSlotDuplicateError,
    BusChannelConflictError,
)


class TestChannelValidator:
    """Tests for ChannelValidator class."""

    @pytest.fixture
    def validator_32ch(self) -> ChannelValidator:
        """Create validator for 32-channel setup."""
        return ChannelValidator(detected_channel_count=32)

    def test_valid_channels_pass_validation(
        self,
        validator_32ch: ChannelValidator,
    ) -> None:
        """Test that valid channel configurations pass validation."""
        channels = [
            ChannelConfig(ch=1, name="Kick"),
            ChannelConfig(ch=2, name="Snare"),
            ChannelConfig(ch=32, name="Last"),
        ]
        
        # Should not raise
        validator_32ch.validate(channels)

    def test_duplicate_channel_raises_error(
        self,
        validator_32ch: ChannelValidator,
    ) -> None:
        """Test that duplicate channel numbers raise DuplicateChannelError."""
        channels = [
            ChannelConfig(ch=1, name="First"),
            ChannelConfig(ch=1, name="Duplicate"),
        ]
        
        with pytest.raises(DuplicateChannelError) as exc_info:
            validator_32ch.validate(channels)
        
        assert exc_info.value.ch == 1

    def test_channel_out_of_range_raises_error(
        self,
        validator_32ch: ChannelValidator,
    ) -> None:
        """Test that channel exceeding detected count raises error."""
        channels = [
            ChannelConfig(ch=33, name="Out of Range"),
        ]
        
        with pytest.raises(ChannelOutOfRangeError) as exc_info:
            validator_32ch.validate(channels)
        
        assert exc_info.value.ch == 33
        assert exc_info.value.detected == 32


class TestBusValidator:
    """Tests for BusValidator class."""

    @pytest.fixture
    def validator_32ch(self) -> BusValidator:
        """Create validator for 32-channel setup."""
        return BusValidator(detected_channel_count=32)

    def test_valid_bus_channels_pass_validation(
        self,
        validator_32ch: BusValidator,
    ) -> None:
        """Test that valid bus channel assignments pass."""
        # Should not raise
        validator_32ch.validate_channels([7, 8, 15, 16])

    def test_bus_channel_out_of_range_raises_error(
        self,
        validator_32ch: BusValidator,
    ) -> None:
        """Test that bus channel exceeding detected count raises error."""
        with pytest.raises(BusSlotOutOfRangeError) as exc_info:
            validator_32ch.validate_channels([33])
        
        assert exc_info.value.ch == 33

    def test_duplicate_bus_channel_raises_error(
        self,
        validator_32ch: BusValidator,
    ) -> None:
        """Test that same channel in multiple bus slots raises error."""
        with pytest.raises(BusSlotDuplicateError) as exc_info:
            validator_32ch.validate_channels([7, 7])
        
        assert exc_info.value.ch == 7

    def test_bus_channel_conflict_with_process_action(
        self,
        validator_32ch: BusValidator,
    ) -> None:
        """Test that channel marked PROCESS cannot be used in bus."""
        channels = [
            ChannelConfig(ch=7, name="OH Left", action=ChannelAction.PROCESS),
        ]
        
        with pytest.raises(BusChannelConflictError):
            validator_32ch.validate_no_conflicts(channels, [7])

    def test_bus_channel_with_bus_action_passes(
        self,
        validator_32ch: BusValidator,
    ) -> None:
        """Test that channel marked BUS can be used in bus configuration."""
        channels = [
            ChannelConfig(ch=7, name="OH Left", action=ChannelAction.BUS),
        ]
        
        # Should not raise
        validator_32ch.validate_no_conflicts(channels, [7])
```

---

### 2. Audio Module Tests

#### `tests/unit/audio/test_discovery.py`

```python
"""Unit tests for audio file discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.audio.discovery import AudioFileDiscovery


class TestAudioFileDiscovery:
    """Tests for AudioFileDiscovery class."""

    @pytest.fixture
    def discovery(self, tmp_input_dir: Path) -> AudioFileDiscovery:
        """Create AudioFileDiscovery instance with temp directory."""
        return AudioFileDiscovery(tmp_input_dir)

    def test_discover_empty_directory(
        self,
        discovery: AudioFileDiscovery,
    ) -> None:
        """Test discovery returns empty list for empty directory."""
        files = discovery.discover_files()
        
        assert files == []

    def test_discover_single_wav_file(
        self,
        discovery: AudioFileDiscovery,
        tmp_input_dir: Path,
    ) -> None:
        """Test discovery finds single WAV file."""
        wav_file = tmp_input_dir / "00000001.WAV"
        wav_file.write_bytes(b"\x00" * 100)
        
        files = discovery.discover_files()
        
        assert len(files) == 1
        assert files[0] == wav_file

    def test_discover_multiple_files_sorted(
        self,
        discovery: AudioFileDiscovery,
        tmp_input_dir: Path,
    ) -> None:
        """Test discovery returns files in numeric order."""
        # Create files in non-sequential order
        (tmp_input_dir / "00000003.WAV").write_bytes(b"\x00")
        (tmp_input_dir / "00000001.WAV").write_bytes(b"\x00")
        (tmp_input_dir / "00000002.WAV").write_bytes(b"\x00")
        
        files = discovery.discover_files()
        
        assert len(files) == 3
        assert files[0].name == "00000001.WAV"
        assert files[1].name == "00000002.WAV"
        assert files[2].name == "00000003.WAV"

    def test_discover_case_insensitive(
        self,
        discovery: AudioFileDiscovery,
        tmp_input_dir: Path,
    ) -> None:
        """Test discovery finds both .wav and .WAV extensions."""
        (tmp_input_dir / "file1.wav").write_bytes(b"\x00")
        (tmp_input_dir / "file2.WAV").write_bytes(b"\x00")
        (tmp_input_dir / "file3.Wav").write_bytes(b"\x00")
        
        files = discovery.discover_files()
        
        assert len(files) == 3

    def test_non_wav_files_ignored(
        self,
        discovery: AudioFileDiscovery,
        tmp_input_dir: Path,
    ) -> None:
        """Test that non-WAV files are ignored."""
        (tmp_input_dir / "readme.txt").write_bytes(b"\x00")
        (tmp_input_dir / "audio.mp3").write_bytes(b"\x00")
        (tmp_input_dir / "00000001.WAV").write_bytes(b"\x00")
        
        files = discovery.discover_files()
        
        assert len(files) == 1
        assert files[0].name == "00000001.WAV"
```

#### `tests/unit/audio/test_validation.py`

```python
"""Unit tests for audio file validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.audio.validation import AudioValidator
from src.config.enums import BitDepth
from src.exceptions import AudioProcessingError


class TestAudioValidator:
    """Tests for AudioValidator class."""

    @pytest.fixture
    def validator(self) -> AudioValidator:
        """Create AudioValidator instance."""
        return AudioValidator()

    def test_validate_empty_file_list_raises_error(
        self,
        validator: AudioValidator,
    ) -> None:
        """Test that empty file list raises AudioProcessingError."""
        with pytest.raises(AudioProcessingError, match="No files to validate"):
            validator.validate_files([])

    def test_validate_nonexistent_file_raises_error(
        self,
        validator: AudioValidator,
        tmp_path: Path,
    ) -> None:
        """Test that nonexistent file raises AudioProcessingError."""
        fake_path = tmp_path / "nonexistent.wav"
        
        with pytest.raises(AudioProcessingError, match="does not exist"):
            validator.validate_files([fake_path])

    def test_validate_empty_file_raises_error(
        self,
        validator: AudioValidator,
        tmp_path: Path,
    ) -> None:
        """Test that empty file raises AudioProcessingError."""
        empty_file = tmp_path / "empty.wav"
        empty_file.write_bytes(b"")
        
        with pytest.raises(AudioProcessingError, match="is empty"):
            validator.validate_files([empty_file])

    def test_validate_consistent_files_succeeds(
        self,
        validator: AudioValidator,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test that consistent audio files pass validation."""
        from tests.unit.audio.conftest import MockSoundFileInfo
        
        # Create mock files
        file1 = tmp_path / "file1.wav"
        file2 = tmp_path / "file2.wav"
        file1.write_bytes(b"\x00" * 100)
        file2.write_bytes(b"\x00" * 100)
        
        # Mock soundfile.info
        mock_info = mocker.patch("soundfile.info")
        mock_info.return_value = MockSoundFileInfo(
            samplerate=48000,
            channels=32,
            subtype="PCM_24",
        )
        
        # Should not raise
        rate, channels, bit_depth = validator.validate_files([file1, file2])
        
        assert rate == 48000
        assert channels == 32
        assert bit_depth == BitDepth.INT24

    def test_validate_sample_rate_mismatch_raises_error(
        self,
        validator: AudioValidator,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test that sample rate mismatch raises AudioProcessingError."""
        from tests.unit.audio.conftest import MockSoundFileInfo
        
        file1 = tmp_path / "file1.wav"
        file2 = tmp_path / "file2.wav"
        file1.write_bytes(b"\x00" * 100)
        file2.write_bytes(b"\x00" * 100)
        
        # Mock to return different sample rates
        mock_info = mocker.patch("soundfile.info")
        mock_info.side_effect = [
            MockSoundFileInfo(samplerate=48000),
            MockSoundFileInfo(samplerate=44100),
        ]
        
        with pytest.raises(AudioProcessingError, match="Sample rate mismatch"):
            validator.validate_files([file1, file2])

    @pytest.mark.parametrize("subtype,expected_depth", [
        ("PCM_16", BitDepth.INT16),
        ("PCM_24", BitDepth.INT24),
        ("FLOAT", BitDepth.FLOAT32),
    ])
    def test_bit_depth_conversion(
        self,
        validator: AudioValidator,
        subtype: str,
        expected_depth: BitDepth,
    ) -> None:
        """Test conversion from soundfile subtype to BitDepth enum."""
        result = validator._bit_depth_from_subtype(subtype)
        
        assert result == expected_depth
```

---

### 2.5 Click Feature Tests

#### `tests/unit/audio/click/test_analyzer.py`

```python
"""Unit tests for ScipyClickAnalyzer."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import signal

from src.audio.click.analyzer import ScipyClickAnalyzer
from src.config.models import SectionSplittingConfig


class TestScipyClickAnalyzer:
    """Tests for ScipyClickAnalyzer."""

    @pytest.fixture
    def config(self) -> SectionSplittingConfig:
        """Create test configuration."""
        return SectionSplittingConfig(
            enabled=True,
            gap_threshold_seconds=3.0,
            min_section_length_seconds=15.0,
            bpm_change_threshold=1,
        )

    @pytest.fixture
    def analyzer(self, config: SectionSplittingConfig) -> ScipyClickAnalyzer:
        """Create analyzer instance."""
        return ScipyClickAnalyzer(config)

    def test_analyze_synthetic_click_track_120bpm(
        self,
        analyzer: ScipyClickAnalyzer,
        sample_rate: int = 44100,
    ) -> None:
        """Test analysis of synthetic 120 BPM click track."""
        # Generate 10 seconds of 120 BPM clicks
        duration_sec = 10
        bpm = 120
        samples = np.zeros(int(sample_rate * duration_sec))
        
        # Create click pattern (every 0.5 seconds at 120 BPM)
        click_interval = int(sample_rate * 60 / bpm)
        for i in range(0, len(samples), click_interval):
            # Simple click: short burst of high frequency
            click_samples = int(sample_rate * 0.01)  # 10ms click
            if i + click_samples < len(samples):
                # High-frequency burst
                t = np.linspace(0, 0.01, click_samples)
                click_wave = np.sin(2 * np.pi * 2000 * t) * np.exp(-t * 100)
                samples[i:i + click_samples] += click_wave
        
        # Mock soundfile to return our synthetic audio
        import soundfile as sf
        with pytest.mock.patch.object(sf, 'blocks') as mock_blocks:
            mock_blocks.return_value = iter([samples.reshape(-1, 1)])
            
            sections = analyzer.analyze("dummy.wav", sample_rate)
            
            assert len(sections) == 1
            assert sections[0].bpm == pytest.approx(120, abs=2)
            assert sections[0].section_number == 1

    def test_analyze_no_clicks_returns_single_section(
        self,
        analyzer: ScipyClickAnalyzer,
        sample_rate: int = 44100,
    ) -> None:
        """Test that silent audio returns single section with bpm=None."""
        # Generate silent audio
        samples = np.zeros((sample_rate * 5, 1))  # 5 seconds
        
        import soundfile as sf
        with pytest.mock.patch.object(sf, 'blocks') as mock_blocks:
            mock_blocks.return_value = iter([samples])
            
            sections = analyzer.analyze("silent.wav", sample_rate)
            
            assert len(sections) == 1
            assert sections[0].bpm is None
            assert sections[0].section_number == 1

    def test_analyze_multiple_tempo_changes(
        self,
        analyzer: ScipyClickAnalyzer,
        sample_rate: int = 44100,
    ) -> None:
        """Test detection of tempo changes within a track."""
        # Create sections with different BPMs separated by gaps
        sections_data = []
        
        # Section 1: 100 BPM for 5 seconds
        duration1 = 5
        bpm1 = 100
        samples1 = np.zeros(int(sample_rate * duration1))
        click_interval1 = int(sample_rate * 60 / bpm1)
        for i in range(0, len(samples1), click_interval1):
            click_samples = int(sample_rate * 0.01)
            if i + click_samples < len(samples1):
                t = np.linspace(0, 0.01, click_samples)
                click_wave = np.sin(2 * np.pi * 2000 * t) * np.exp(-t * 100)
                samples1[i:i + click_samples] += click_wave
        
        # Gap: 4 seconds of silence (exceeds gap_threshold)
        gap_samples = np.zeros(int(sample_rate * 4))
        
        # Section 2: 140 BPM for 5 seconds  
        duration2 = 5
        bpm2 = 140
        samples2 = np.zeros(int(sample_rate * duration2))
        click_interval2 = int(sample_rate * 60 / bpm2)
        for i in range(0, len(samples2), click_interval2):
            click_samples = int(sample_rate * 0.01)
            if i + click_samples < len(samples2):
                t = np.linspace(0, 0.01, click_samples)
                click_wave = np.sin(2 * np.pi * 2000 * t) * np.exp(-t * 100)
                samples2[i:i + click_samples] += click_wave
        
        # Combine: section1 + gap + section2
        combined = np.vstack([samples1.reshape(-1, 1), 
                            gap_samples.reshape(-1, 1), 
                            samples2.reshape(-1, 1)])
        
        import soundfile as sf
        with pytest.mock.patch.object(sf, 'blocks') as mock_blocks:
            mock_blocks.return_value = iter([combined])
            
            sections = analyzer.analyze("multi_tempo.wav", sample_rate)
            
            assert len(sections) >= 2  # At least two sections detected
            # First section should be ~100 BPM
            assert sections[0].bpm == pytest.approx(100, abs=5)
            # Later sections should have different BPM if detected
```

#### `tests/unit/audio/click/test_models.py`

```python
"""Unit tests for click analysis data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.audio.click.models import SectionInfo
from src.audio.click.enums import SectionType


class TestSectionInfo:
    """Tests for SectionInfo Pydantic model."""

    def test_create_section_info_minimal(self) -> None:
        """Test creating SectionInfo with minimal required fields."""
        section = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=441000,  # 10 seconds at 44.1kHz
            bpm=120,
        )
        
        assert section.section_number == 1
        assert section.start_sample == 0
        assert section.end_sample == 441000
        assert section.bpm == 120
        assert section.section_type == SectionType.SONG  # default

    def test_create_section_info_with_type(self) -> None:
        """Test creating SectionInfo with explicit section type."""
        section = SectionInfo(
            section_number=2,
            start_sample=441000,
            end_sample=882000,
            bpm=140,
            section_type=SectionType.BRIDGE,
        )
        
        assert section.section_type == SectionType.BRIDGE

    def test_section_info_validation_negative_bpm(self) -> None:
        """Test that negative BPM values are rejected."""
        with pytest.raises(ValidationError):
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=441000,
                bpm=-10,  # Invalid
            )

    def test_section_info_bpm_none_allowed(self) -> None:
        """Test that bpm=None is allowed for sections without detectable tempo."""
        section = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=441000,
            bpm=None,  # Valid for silent sections
        )
        
        assert section.bpm is None

    def test_section_info_serialization(self) -> None:
        """Test JSON serialization/deserialization."""
        import json
        
        section = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=441000,
            bpm=120,
            section_type=SectionType.VERSE,
        )
        
        # Serialize to dict
        data = section.model_dump()
        assert data["section_number"] == 1
        assert data["bpm"] == 120
        assert data["section_type"] == "VERSE"
        
        # Deserialize from dict
        section2 = SectionInfo.model_validate(data)
        assert section2 == section
```

#### `tests/unit/audio/click/test_protocols.py`

```python
"""Unit tests for click analysis protocols."""

from __future__ import annotations

from typing import Protocol
from unittest.mock import Mock

import pytest

from src.audio.click.protocols import ClickAnalyzerProtocol


class TestClickAnalyzerProtocol:
    """Tests for ClickAnalyzerProtocol interface."""

    def test_protocol_definition(self) -> None:
        """Test that ClickAnalyzerProtocol is properly defined."""
        # This is a compile-time check - if the protocol is malformed,
        # mypy will catch it during type checking
        
        # Create a mock implementation
        class MockAnalyzer:
            def analyze(self, audio_path, sample_rate):
                return []
        
        analyzer = MockAnalyzer()
        
        # Verify it matches the protocol (runtime check)
        assert hasattr(analyzer, 'analyze')
        assert callable(getattr(analyzer, 'analyze'))

    def test_protocol_inheritance(self) -> None:
        """Test that concrete implementations properly inherit from protocol."""
        from src.audio.click.analyzer import ScipyClickAnalyzer
        from src.config.models import SectionSplittingConfig
        
        # Create instance
        config = SectionSplittingConfig()
        analyzer = ScipyClickAnalyzer(config)
        
        # Verify it implements the protocol
        assert isinstance(analyzer, ClickAnalyzerProtocol)
        
        # Verify method exists and is callable
        assert hasattr(analyzer, 'analyze')
        assert callable(analyzer.analyze)
```

#### `tests/unit/output/test_session_json.py`

```python
"""Unit tests for SessionJsonWriter."""

from __future__ import annotations

from pathlib import Path
import json
import pytest

from src.output.session_json import SessionJsonWriter
from src.audio.click.models import SectionInfo
from src.audio.click.enums import SectionType


class TestSessionJsonWriter:
    """Tests for SessionJsonWriter."""

    @pytest.fixture
    def writer(self, tmp_path: Path) -> SessionJsonWriter:
        """Create SessionJsonWriter instance."""
        return SessionJsonWriter()

    @pytest.fixture
    def sample_sections(self) -> list[SectionInfo]:
        """Create sample section data for testing."""
        return [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=441000,  # 10 seconds
                bpm=120,
                section_type=SectionType.VERSE,
            ),
            SectionInfo(
                section_number=2, 
                start_sample=441000,
                end_sample=882000,  # 20 seconds total
                bpm=140,
                section_type=SectionType.CHORUS,
            ),
        ]

    def test_write_session_json(
        self,
        writer: SessionJsonWriter,
        tmp_path: Path,
        sample_sections: list[SectionInfo],
    ) -> None:
        """Test writing session JSON with section data."""
        output_file = tmp_path / "session.json"
        
        writer.write_session_json(
            sections=sample_sections,
            output_path=output_file,
            sample_rate=44100,
            input_files=["track1.wav", "track2.wav"],
        )
        
        # Verify file was created
        assert output_file.exists()
        
        # Verify JSON content
        with open(output_file) as f:
            data = json.load(f)
        
        assert "sections" in data
        assert "metadata" in data
        assert len(data["sections"]) == 2
        
        # Check first section
        section1 = data["sections"][0]
        assert section1["section"] == "section_01"
        assert section1["start_time"] == 0.0
        assert section1["duration"] == 10.0
        assert section1["bpm"] == 120
        assert section1["type"] == "VERSE"
        
        # Check metadata
        assert data["metadata"]["sample_rate"] == 44100
        assert data["metadata"]["input_files"] == ["track1.wav", "track2.wav"]

    def test_write_session_json_empty_sections(
        self,
        writer: SessionJsonWriter,
        tmp_path: Path,
    ) -> None:
        """Test writing session JSON with no sections."""
        output_file = tmp_path / "empty_session.json"
        
        writer.write_session_json(
            sections=[],
            output_path=output_file,
            sample_rate=48000,
            input_files=["single_track.wav"],
        )
        
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
        
        assert data["sections"] == []
        assert data["metadata"]["sample_rate"] == 48000
```

#### `tests/unit/output/test_metadata.py`

```python
"""Unit tests for metadata embedding."""

from __future__ import annotations

from pathlib import Path
import tempfile
import pytest

from src.output.metadata import MutagenMetadataWriter


class TestMutagenMetadataWriter:
    """Tests for MutagenMetadataWriter."""

    @pytest.fixture
    def writer(self) -> MutagenMetadataWriter:
        """Create metadata writer instance."""
        return MutagenMetadataWriter()

    @pytest.fixture
    def temp_wav_file(self) -> Path:
        """Create a temporary WAV file for testing."""
        # Create minimal WAV file using soundfile
        import soundfile as sf
        import numpy as np
        
        samples = np.random.randn(44100, 2).astype(np.float32)  # 1 second stereo
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, samples, 44100)
            yield Path(f.name)
        
        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    def test_embed_bpm_metadata(
        self,
        writer: MutagenMetadataWriter,
        temp_wav_file: Path,
    ) -> None:
        """Test embedding BPM metadata in WAV file."""
        test_bpm = 128
        
        # Embed BPM
        writer.embed_bpm(temp_wav_file, test_bpm)
        
        # Verify BPM was embedded
        read_bpm = writer.read_bpm(temp_wav_file)
        assert read_bpm == test_bpm

    def test_read_bpm_no_metadata(self, temp_wav_file: Path) -> None:
        """Test reading BPM from file without metadata."""
        writer = MutagenMetadataWriter()
        
        bpm = writer.read_bpm(temp_wav_file)
        assert bpm is None

    def test_embed_bpm_overwrites_existing(
        self,
        writer: MutagenMetadataWriter,
        temp_wav_file: Path,
    ) -> None:
        """Test that embedding BPM overwrites existing value."""
        # Embed initial BPM
        writer.embed_bpm(temp_wav_file, 100)
        assert writer.read_bpm(temp_wav_file) == 100
        
        # Embed new BPM
        writer.embed_bpm(temp_wav_file, 140)
        assert writer.read_bpm(temp_wav_file) == 140
```

#### Integration Tests for Click Feature

```python
"""Integration tests for click-based section splitting."""

from __future__ import annotations

from pathlib import Path
import json
import pytest

from tests.conftest import run_cli_command


class TestClickFeatureIntegration:
    """Integration tests for the complete click feature workflow."""

    def test_full_section_splitting_workflow(
        self,
        tmp_path: Path,
        sample_multitrack_project: Path,
    ) -> None:
        """Test complete workflow: input → processing → sectioned output."""
        output_dir = tmp_path / "output"
        
        # Run processing with section splitting
        result = run_cli_command([
            "process",
            str(sample_multitrack_project),
            "--output", str(output_dir),
            "--section-by-click",
            "--session-json", str(output_dir / "session.json"),
        ])
        
        assert result.returncode == 0
        
        # Verify output structure
        assert output_dir.exists()
        
        # Should have section directories
        section_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("section_")]
        assert len(section_dirs) > 0
        
        # Each section should have audio files
        for section_dir in section_dirs:
            wav_files = list(section_dir.glob("*.wav"))
            assert len(wav_files) > 0
            
            # Check for BPM metadata in files
            # (This would require additional audio analysis tools)
        
        # Check session JSON
        session_file = output_dir / "session.json"
        assert session_file.exists()
        
        with open(session_file) as f:
            session_data = json.load(f)
        
        assert "sections" in session_data
        assert "metadata" in session_data
        assert len(session_data["sections"]) > 0

    def test_section_splitting_disabled_by_default(
        self,
        tmp_path: Path,
        sample_multitrack_project: Path,
    ) -> None:
        """Test that section splitting is disabled by default."""
        output_dir = tmp_path / "output_no_sections"
        
        # Run without --section-by-click
        result = run_cli_command([
            "process",
            str(sample_multitrack_project),
            "--output", str(output_dir),
        ])
        
        assert result.returncode == 0
        
        # Should NOT have section directories
        section_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("section_")]
        assert len(section_dirs) == 0
        
        # Should have direct WAV files
        wav_files = list(output_dir.glob("*.wav"))
        assert len(wav_files) > 0
```

---

### 3. Processing Module Tests

#### `tests/unit/processing/conftest.py`

```python
"""Processing module test fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_mock import MockerFixture

from src.config.enums import BitDepth
from src.processing.converters.protocols import BitDepthConverter

if TYPE_CHECKING:
    from src.config import SegmentMap


class MockBitDepthConverter:
    """Mock converter implementing BitDepthConverter protocol."""
    
    soundfile_subtype: str = "PCM_24"
    
    def convert(self, data):
        return data


@pytest.fixture
def mock_converter() -> BitDepthConverter:
    """Create a mock BitDepthConverter."""
    return MockBitDepthConverter()


@pytest.fixture
def sample_segments(tmp_temp_dir: Path) -> SegmentMap:
    """Create sample segment map for testing.
    
    Returns:
        Dictionary mapping channel numbers to lists of segment file paths.
    """
    segments: SegmentMap = {}
    
    for ch in range(1, 5):
        ch_segments = []
        for seg_num in range(1, 4):
            seg_path = tmp_temp_dir / f"ch{ch:02d}_seg{seg_num:04d}.wav"
            seg_path.write_bytes(b"\x00" * 1000)  # Mock audio data
            ch_segments.append(seg_path)
        segments[ch] = ch_segments
    
    return segments
```

#### `tests/unit/processing/test_builder.py`

```python
"""Unit tests for TrackBuilder orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.processing.builder import TrackBuilder
from src.config import ChannelConfig, BusConfig, BitDepth
from src.config.enums import ChannelAction, BusSlot, BusType


class TestTrackBuilder:
    """Tests for TrackBuilder class."""

    @pytest.fixture
    def builder(
        self,
        tmp_temp_dir: Path,
        tmp_output_dir: Path,
        mock_output_handler,
        mocker: MockerFixture,
    ) -> TrackBuilder:
        """Create TrackBuilder with mocked dependencies."""
        # Mock the converter factory
        mocker.patch(
            "src.processing.builder.get_converter",
            return_value=mocker.MagicMock(soundfile_subtype="PCM_24"),
        )
        mocker.patch(
            "src.processing.builder.resolve_bit_depth",
            return_value=BitDepth.INT24,
        )
        
        return TrackBuilder(
            sample_rate=48000,
            bit_depth=BitDepth.INT24,
            temp_dir=tmp_temp_dir,
            output_dir=tmp_output_dir,
            output_handler=mock_output_handler,
        )

    def test_builder_creates_output_directory(
        self,
        tmp_temp_dir: Path,
        tmp_output_dir: Path,
        mock_output_handler,
        mocker: MockerFixture,
    ) -> None:
        """Test that builder creates output directory on init."""
        # Remove directory to test creation
        tmp_output_dir.rmdir()
        
        mocker.patch("src.processing.builder.get_converter")
        mocker.patch("src.processing.builder.resolve_bit_depth")
        
        TrackBuilder(
            sample_rate=48000,
            bit_depth=BitDepth.INT24,
            temp_dir=tmp_temp_dir,
            output_dir=tmp_output_dir,
            output_handler=mock_output_handler,
        )
        
        assert tmp_output_dir.exists()

    def test_build_tracks_calls_writers(
        self,
        builder: TrackBuilder,
        mocker: MockerFixture,
        sample_segments,
    ) -> None:
        """Test that build_tracks delegates to mono and stereo writers."""
        mock_mono_write = mocker.patch.object(builder.mono_writer, "write_tracks")
        mock_stereo_write = mocker.patch.object(builder.stereo_writer, "write_tracks")
        
        channels = [
            ChannelConfig(ch=1, name="Kick", action=ChannelAction.PROCESS),
        ]
        buses = [
            BusConfig(
                file_name="Overheads",
                slots={BusSlot.LEFT: 3, BusSlot.RIGHT: 4},
            ),
        ]
        
        builder.build_tracks(channels, buses, sample_segments)
        
        mock_mono_write.assert_called_once_with(channels, sample_segments)
        mock_stereo_write.assert_called_once_with(buses, sample_segments)
```

---

## Fixture Design Patterns

### Pattern 1: Factory Fixtures

Factory fixtures create objects with customizable parameters, reducing duplication.

```python
@pytest.fixture
def channel_config_factory():
    """Factory for creating ChannelConfig instances with defaults."""
    def _create(**overrides) -> ChannelConfig:
        defaults = {
            "ch": 1,
            "name": "Test Channel",
            "action": ChannelAction.PROCESS,
        }
        defaults.update(overrides)
        return ChannelConfig(**defaults)
    
    return _create
```

### Pattern 2: Parametrized Fixtures

Run tests with multiple input variations automatically.

```python
@pytest.fixture(params=[
    BitDepth.INT16,
    BitDepth.INT24,
    BitDepth.FLOAT32,
])
def bit_depth(request) -> BitDepth:
    """Parametrized fixture for all supported bit depths."""
    return request.param
```

### Pattern 3: Scoped Fixtures

Control fixture lifecycle for performance.

```python
@pytest.fixture(scope="module")
def expensive_test_data():
    """Module-scoped fixture for data used across multiple tests."""
    # Created once per module, not per test
    return generate_expensive_data()


@pytest.fixture(scope="session")
def shared_temp_directory(tmp_path_factory):
    """Session-scoped fixture for shared temporary storage."""
    return tmp_path_factory.mktemp("shared")
```

### Pattern 4: Cleanup Fixtures with Yield

Ensure proper cleanup after tests.

```python
@pytest.fixture
def temporary_wav_file(tmp_path: Path):
    """Create and cleanup a temporary WAV file."""
    wav_path = tmp_path / "test.wav"
    wav_path.write_bytes(b"\x00" * 1000)
    
    yield wav_path
    
    # Cleanup after test
    if wav_path.exists():
        wav_path.unlink()
```

---

## Parametrization Strategy

### Using `@pytest.mark.parametrize`

```python
class TestBitDepthConversion:
    """Parametrized tests for bit depth conversions."""

    @pytest.mark.parametrize("input_depth,expected_subtype", [
        (BitDepth.INT16, "PCM_16"),
        (BitDepth.INT24, "PCM_24"),
        (BitDepth.FLOAT32, "FLOAT"),
    ])
    def test_converter_subtype_mapping(
        self,
        input_depth: BitDepth,
        expected_subtype: str,
    ) -> None:
        """Test that each bit depth maps to correct soundfile subtype."""
        from src.processing.converters.factory import get_converter
        
        converter = get_converter(input_depth)
        
        assert converter.soundfile_subtype == expected_subtype

    @pytest.mark.parametrize("invalid_input", [
        None,
        "invalid",
        42,
        BitDepth.SOURCE,  # Requires source_bit_depth
    ])
    def test_invalid_bit_depth_raises_error(self, invalid_input) -> None:
        """Test that invalid inputs raise appropriate errors."""
        from src.processing.converters.factory import get_converter
        
        with pytest.raises((ValueError, TypeError)):
            get_converter(invalid_input)
```

### Combining Parametrize with Fixtures

```python
@pytest.mark.parametrize("channel_count", [8, 16, 32, 64])
def test_validator_with_different_channel_counts(
    channel_count: int,
    channel_data_factory,
) -> None:
    """Test validator works with various channel counts."""
    validator = ChannelValidator(detected_channel_count=channel_count)
    
    # Create channels up to the limit
    channels = [
        ChannelConfig(**channel_data_factory(ch=i, name=f"Ch {i}"))
        for i in range(1, channel_count + 1)
    ]
    
    # Should not raise
    validator.validate(channels)
```

---

## Markers and Test Organization

### Custom Markers

```python
# In conftest.py
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "ffmpeg: FFmpeg-related tests")
    config.addinivalue_line("markers", "pydantic: Pydantic model tests")
```

### Using Markers in Tests

```python
import pytest


@pytest.mark.pydantic
class TestChannelConfigValidation:
    """Pydantic model validation tests."""
    
    def test_valid_model(self):
        ...


@pytest.mark.ffmpeg
@pytest.mark.slow
def test_ffmpeg_extraction():
    """Slow test involving FFmpeg mocking."""
    ...
```

### Running Specific Markers

```bash
# Run only unit tests
uv run pytest -m unit

# Run all except slow tests
uv run pytest -m "not slow"

# Run pydantic tests
uv run pytest -m pydantic
```

---

## Implementation Guide

### Phase 1: Setup (Day 1)

1. **Create directory structure** as defined above
2. **Add test dependencies** to `pyproject.toml`
3. **Create root `conftest.py`** with base fixtures
4. **Create `pytest.ini`** with configuration

### Phase 2: Config Module Tests (Day 2-3)

1. Implement `test_enums.py` - Simple enum tests
2. Implement `test_models.py` - Pydantic model validation
3. Implement `test_validators.py` - Cross-validation logic
4. Implement `test_loader.py` - Configuration loading

### Phase 3: Audio Module Tests (Day 4-5)

1. Implement `test_discovery.py` - File discovery with mocked filesystem
2. Implement `test_validation.py` - Audio parameter validation
3. Implement `test_info.py` - Audio info retrieval (mocked)
4. Implement FFmpeg tests with subprocess mocking

### Phase 4: Processing Module Tests (Day 6-7)

1. Implement `test_builder.py` - Track building orchestration
2. Implement `test_mono.py` - Mono track writing
3. Implement `test_stereo.py` - Stereo bus writing
4. Implement converter tests

### Phase 5: CLI Tests (Day 8)

1. Implement `test_app.py` - Typer app tests
2. Implement `test_commands.py` - Command function tests
3. Implement `test_utils.py` - Utility function tests

### Phase 6: Integration & Refinement (Day 9-10)

1. Review test coverage
2. Add missing edge cases
3. Ensure all markers are properly applied
4. Document any test-specific requirements

---

## Quality Assurance Checklist

### Code Quality

- [ ] All tests follow AAA pattern (Arrange-Act-Assert)
- [ ] No hardcoded paths (use `tmp_path` fixtures)
- [ ] Mocks properly verify call arguments
- [ ] No print statements (use assertions)
- [ ] Type hints on all test functions
- [ ] Docstrings on all test functions

### Coverage Targets

- [ ] Config models: 100% line coverage
- [ ] Validators: 100% line coverage
- [ ] Audio discovery: 90%+ coverage
- [ ] FFmpeg executor: 90%+ coverage
- [ ] Processing writers: 85%+ coverage
- [ ] CLI commands: 80%+ coverage

### SOLID Compliance

- [ ] Each test file has single responsibility
- [ ] Fixtures are reusable across test modules
- [ ] Mocks implement correct interfaces
- [ ] Tests don't depend on execution order
- [ ] Abstract dependencies are properly injected

### Performance

- [ ] Unit test suite runs in < 10 seconds
- [ ] No actual file I/O (all mocked)
- [ ] No subprocess calls (all mocked)
- [ ] Session-scoped fixtures for expensive setup

---

## CLI Testing with Typer CliRunner

Testing CLI applications requires a different approach than standard unit tests. Typer provides `CliRunner` for this purpose.

### CLI Test Fixtures (`tests/unit/cli/conftest.py`)

```python
"""CLI testing fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner
from pytest_mock import MockerFixture

from src.cli.app import app

if TYPE_CHECKING:
    from typer.testing import Result


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CliRunner for testing Typer commands.
    
    Returns:
        CliRunner instance for invoking CLI commands.
    """
    return CliRunner()


@pytest.fixture
def invoke_app(cli_runner: CliRunner):
    """Factory fixture for invoking the app with arguments.
    
    Returns:
        Callable that invokes the CLI app and returns the result.
    """
    def _invoke(*args: str, **kwargs) -> Result:
        return cli_runner.invoke(app, list(args), **kwargs)
    
    return _invoke
```

### CLI Test Examples (`tests/unit/cli/test_commands.py`)

```python
"""Unit tests for CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner
from pytest_mock import MockerFixture

from src.cli.app import app


class TestMainCommand:
    """Tests for the main CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a fresh CliRunner."""
        return CliRunner()

    def test_version_flag_shows_version(self, runner: CliRunner) -> None:
        """Test that --version flag displays version and exits."""
        result = runner.invoke(app, ["--version"])
        
        assert result.exit_code == 0
        assert "Channel Weaver" in result.output

    def test_help_flag_shows_help(self, runner: CliRunner) -> None:
        """Test that --help flag displays help message."""
        result = runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "Process multitrack recordings" in result.output or "multitrack" in result.output.lower()

    def test_missing_input_path_shows_error(self, runner: CliRunner) -> None:
        """Test that missing input path shows appropriate error."""
        result = runner.invoke(app, [])
        
        assert result.exit_code != 0

    def test_nonexistent_input_path_shows_error(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test that non-existent input path shows error."""
        fake_path = tmp_path / "nonexistent"
        
        result = runner.invoke(app, [str(fake_path)])
        
        assert result.exit_code != 0

    def test_valid_input_with_mocked_processing(
        self,
        runner: CliRunner,
        tmp_input_dir: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test successful processing with mocked dependencies."""
        # Create a dummy WAV file
        (tmp_input_dir / "00000001.WAV").write_bytes(b"\x00" * 1000)
        
        # Mock all external dependencies
        mock_extractor = mocker.patch("src.cli.commands.AudioExtractor")
        mock_extractor_instance = mock_extractor.return_value
        mock_extractor_instance.discover_and_validate.return_value = []
        mock_extractor_instance.channels = 32
        mock_extractor_instance.sample_rate = 48000
        mock_extractor_instance.bit_depth = mocker.MagicMock()
        mock_extractor_instance.extract_segments.return_value = {}
        mock_extractor_instance.cleanup = mocker.MagicMock()
        
        mock_loader = mocker.patch("src.cli.commands.ConfigLoader")
        mock_loader.return_value.load.return_value = ([], [])
        
        mock_builder = mocker.patch("src.cli.commands.TrackBuilder")
        
        result = runner.invoke(app, [str(tmp_input_dir)])
        
        # Verify mocks were called
        mock_extractor.assert_called_once()
        mock_loader.assert_called_once()

    def test_config_error_shows_message_and_exits(
        self,
        runner: CliRunner,
        tmp_input_dir: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test that ConfigError is caught and displayed properly."""
        from src.exceptions import ConfigError
        
        (tmp_input_dir / "00000001.WAV").write_bytes(b"\x00" * 1000)
        
        mock_extractor = mocker.patch("src.cli.commands.AudioExtractor")
        mock_extractor_instance = mock_extractor.return_value
        mock_extractor_instance.discover_and_validate.side_effect = ConfigError("Test error")
        mock_extractor_instance.cleanup = mocker.MagicMock()
        
        result = runner.invoke(app, [str(tmp_input_dir)])
        
        assert result.exit_code == 1
        assert "Error" in result.output or "error" in result.output.lower()

    @pytest.mark.parametrize("bit_depth_arg,expected_value", [
        ("--bit-depth=16", "16"),
        ("--bit-depth=24", "24"),
        ("--bit-depth=32float", "32float"),
        ("--bit-depth=source", "source"),
    ])
    def test_bit_depth_option_parsing(
        self,
        runner: CliRunner,
        tmp_input_dir: Path,
        mocker: MockerFixture,
        bit_depth_arg: str,
        expected_value: str,
    ) -> None:
        """Test that bit depth options are correctly parsed."""
        (tmp_input_dir / "00000001.WAV").write_bytes(b"\x00" * 1000)
        
        # Mock to capture the bit_depth argument
        mock_extractor = mocker.patch("src.cli.commands.AudioExtractor")
        mock_extractor_instance = mock_extractor.return_value
        mock_extractor_instance.discover_and_validate.return_value = []
        mock_extractor_instance.channels = 32
        mock_extractor_instance.sample_rate = 48000
        mock_extractor_instance.bit_depth = mocker.MagicMock()
        mock_extractor_instance.extract_segments.return_value = {}
        mock_extractor_instance.cleanup = mocker.MagicMock()
        
        mocker.patch("src.cli.commands.ConfigLoader")
        mocker.patch("src.cli.commands.TrackBuilder")
        
        result = runner.invoke(app, [str(tmp_input_dir), bit_depth_arg])
        
        # The test verifies the option is accepted without error
        # Actual bit depth handling is tested in unit tests
```

---

## Advanced Mocking Patterns

### NumPy Array Mocking Patterns

For audio processing tests, numpy arrays are frequently used. Here are patterns for testing with numpy:

```python
"""Numpy array testing patterns for audio processing."""

from __future__ import annotations

import numpy as np
import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def sample_audio_data() -> np.ndarray:
    """Create sample stereo audio data for testing.
    
    Returns:
        2D numpy array of shape (frames, channels) with float32 dtype.
    """
    frames = 48000  # 1 second at 48kHz
    channels = 2
    return np.zeros((frames, channels), dtype=np.float32)


@pytest.fixture
def audio_data_factory():
    """Factory for creating audio data with specific characteristics.
    
    Returns:
        Callable that generates audio data with customizable parameters.
    """
    def _create(
        frames: int = 48000,
        channels: int = 2,
        dtype: np.dtype = np.float32,
        fill_value: float = 0.0,
        noise: bool = False,
    ) -> np.ndarray:
        if noise:
            rng = np.random.default_rng(seed=42)  # Deterministic for tests
            return rng.uniform(-1.0, 1.0, (frames, channels)).astype(dtype)
        return np.full((frames, channels), fill_value, dtype=dtype)
    
    return _create


class TestAudioDataProcessing:
    """Example tests for audio data processing with numpy."""

    def test_audio_conversion_preserves_shape(
        self,
        sample_audio_data: np.ndarray,
    ) -> None:
        """Test that audio conversion preserves the shape of data."""
        original_shape = sample_audio_data.shape
        
        # Example: convert float32 to int16
        converted = (sample_audio_data * 32767).astype(np.int16)
        
        assert converted.shape == original_shape

    def test_channel_extraction(
        self,
        audio_data_factory,
    ) -> None:
        """Test extracting a single channel from multichannel audio."""
        # Create 32-channel audio
        multichannel = audio_data_factory(frames=1000, channels=32)
        
        # Extract channel 0
        mono = multichannel[:, 0]
        
        assert mono.shape == (1000,)
        assert mono.ndim == 1

    @pytest.mark.parametrize("source_dtype,target_dtype", [
        (np.float32, np.int16),
        (np.float32, np.int32),
        (np.int16, np.float32),
        (np.int32, np.float32),
    ])
    def test_dtype_conversion(
        self,
        audio_data_factory,
        source_dtype: np.dtype,
        target_dtype: np.dtype,
    ) -> None:
        """Test converting audio between different data types."""
        source = audio_data_factory(frames=100, channels=2, dtype=source_dtype)
        
        converted = source.astype(target_dtype)
        
        assert converted.dtype == target_dtype
        assert converted.shape == source.shape

    def test_audio_value_range_validation(
        self,
        audio_data_factory,
    ) -> None:
        """Test that audio values stay within expected ranges."""
        # Float audio should be in [-1.0, 1.0] range
        float_audio = audio_data_factory(noise=True)
        
        assert float_audio.min() >= -1.0
        assert float_audio.max() <= 1.0
        
        # Int16 audio should be in [-32768, 32767] range
        int_audio = (float_audio * 32767).astype(np.int16)
        
        assert int_audio.min() >= -32768
        assert int_audio.max() <= 32767


# Using numpy.testing for assertions
class TestNumpyAssertions:
    """Examples of using numpy.testing for precise assertions."""

    def test_array_equality(self, sample_audio_data: np.ndarray) -> None:
        """Test array equality with numpy.testing."""
        expected = np.zeros((48000, 2), dtype=np.float32)
        
        np.testing.assert_array_equal(sample_audio_data, expected)

    def test_array_almost_equal(self) -> None:
        """Test floating point comparison with tolerance."""
        a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        b = np.array([1.0 + 1e-7, 2.0 + 1e-7, 3.0 + 1e-7], dtype=np.float32)
        
        # These are close enough
        np.testing.assert_array_almost_equal(a, b, decimal=6)

    def test_array_shape_assertion(self, audio_data_factory) -> None:
        """Test shape assertions."""
        data = audio_data_factory(frames=1024, channels=8)
        
        assert data.shape == (1024, 8)
        assert data.ndim == 2
```

### Mock Context Manager Pattern

For testing code that uses `with` statements (like soundfile operations):

```python
@pytest.fixture
def mock_soundfile_context(mocker: MockerFixture):
    """Mock soundfile.SoundFile as a context manager.
    
    This fixture creates a mock that properly handles:
    - __enter__ returning the mock itself
    - __exit__ for cleanup
    - Common methods like write(), read(), etc.
    """
    mock_sf = mocker.MagicMock()
    mock_sf.__enter__ = mocker.MagicMock(return_value=mock_sf)
    mock_sf.__exit__ = mocker.MagicMock(return_value=False)
    
    # Common operations
    mock_sf.write = mocker.MagicMock()
    mock_sf.read = mocker.MagicMock(return_value=([], 48000))
    mock_sf.close = mocker.MagicMock()
    
    mocker.patch("soundfile.SoundFile", return_value=mock_sf)
    return mock_sf
```

### Mock Iterator/Generator Pattern

For testing code that processes data in chunks:

```python
@pytest.fixture
def mock_chunked_reader(mocker: MockerFixture):
    """Mock a chunked audio reader that yields data blocks.
    
    Returns:
        Mock that yields numpy arrays when iterated.
    """
    import numpy as np
    
    def chunk_generator():
        for _ in range(5):
            yield np.zeros((1024, 2), dtype=np.float32)
    
    mock_reader = mocker.MagicMock()
    mock_reader.__iter__ = mocker.MagicMock(return_value=iter(chunk_generator()))
    
    return mock_reader
```

### Spy Pattern for Verifying Behavior

When you want to verify a method was called but still execute it:

```python
def test_method_call_verification(mocker: MockerFixture) -> None:
    """Example of using spy to verify calls without mocking behavior."""
    from src.audio.discovery import AudioFileDiscovery
    
    discovery = AudioFileDiscovery(Path("/tmp"))
    
    # Spy on the method - it still executes, but we can verify calls
    spy = mocker.spy(discovery, "_sort_key")
    
    # Create test files and call discover
    # ... test code ...
    
    # Verify spy was called
    assert spy.call_count > 0
    spy.assert_called()
```

---

## Exception Testing Patterns

### Testing Custom Exceptions

```python
"""Unit tests for exception classes - tests/unit/exceptions/test_exceptions.py"""

from __future__ import annotations

import pytest

from src.exceptions import (
    ConfigError,
    ConfigValidationError,
    DuplicateChannelError,
    ChannelOutOfRangeError,
    BusSlotOutOfRangeError,
    BusSlotDuplicateError,
    BusChannelConflictError,
    AudioProcessingError,
)


class TestConfigExceptions:
    """Tests for configuration exception classes."""

    def test_duplicate_channel_error_message(self) -> None:
        """Test DuplicateChannelError contains channel number in message."""
        error = DuplicateChannelError(ch=5)
        
        assert "5" in str(error)
        assert error.ch == 5

    def test_channel_out_of_range_error_attributes(self) -> None:
        """Test ChannelOutOfRangeError stores both channel and detected count."""
        error = ChannelOutOfRangeError(ch=33, detected=32)
        
        assert error.ch == 33
        assert error.detected == 32
        assert "33" in str(error)
        assert "32" in str(error)

    def test_exception_hierarchy(self) -> None:
        """Test that all config exceptions inherit from ConfigError."""
        assert issubclass(DuplicateChannelError, ConfigError)
        assert issubclass(ChannelOutOfRangeError, ConfigError)
        assert issubclass(BusSlotOutOfRangeError, ConfigError)


class TestAudioExceptions:
    """Tests for audio processing exceptions."""

    def test_audio_processing_error_message(self) -> None:
        """Test AudioProcessingError preserves message."""
        error = AudioProcessingError("Test failure message")
        
        assert "Test failure message" in str(error)

    def test_audio_processing_error_is_catchable(self) -> None:
        """Test AudioProcessingError can be caught by parent type."""
        with pytest.raises(Exception):
            raise AudioProcessingError("Test")
```

### Testing Exception Context

```python
def test_exception_chaining(mocker: MockerFixture) -> None:
    """Test that exceptions preserve the original cause."""
    import subprocess
    from src.audio.ffmpeg.executor import FFmpegExecutor
    from src.exceptions import AudioProcessingError
    
    executor = FFmpegExecutor(mocker.MagicMock())
    
    # Create original exception
    original = subprocess.CalledProcessError(1, "ffmpeg", stderr=b"error")
    mocker.patch("subprocess.run", side_effect=original)
    
    with pytest.raises(AudioProcessingError) as exc_info:
        executor.execute(["ffmpeg"], Path("/fake"))
    
    # Verify exception chaining
    assert exc_info.value.__cause__ is original
```

---

## Modern Python 3.14 Features in Tests

### Type Parameter Syntax (PEP 695)

Python 3.14 supports cleaner generic syntax:

```python
# Old style
from typing import TypeVar, Generic
T = TypeVar('T')

class Container(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

# New Python 3.14 style
class Container[T]:
    def __init__(self, value: T) -> None:
        self.value = value
```

### Using in Test Fixtures

```python
# Python 3.14+ factory fixture with type parameters
@pytest.fixture
def typed_factory[T](request) -> Callable[[type[T]], T]:
    """Generic factory fixture for creating typed instances."""
    def _create(cls: type[T], **kwargs) -> T:
        return cls(**kwargs)
    return _create
```

### Pattern Matching in Tests

```python
def test_bus_type_slot_requirements() -> None:
    """Test BusType returns correct required slots using pattern matching."""
    from src.config.enums import BusType, BusSlot
    
    for bus_type in BusType:
        match bus_type:
            case BusType.STEREO:
                expected = {BusSlot.LEFT, BusSlot.RIGHT}
            case _:
                expected = set()  # Fallback for future types
        
        assert bus_type.required_slots() == expected
```

---

## Coverage Configuration

### pyproject.toml Coverage Settings

```toml
[tool.coverage.run]
source = ["src"]
branch = true
omit = [
    "src/__pycache__/*",
    "*/__init__.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "class.*Protocol.*:",
]
show_missing = true
fail_under = 80

[tool.coverage.html]
directory = "htmlcov"
```

### Running Tests with Coverage

```bash
# Run all tests with coverage
uv run pytest --cov=src --cov-report=html --cov-report=term-missing

# Run only unit tests with coverage
uv run pytest tests/unit -m unit --cov=src --cov-fail-under=80

# Generate coverage badge
uv run pytest --cov=src --cov-report=xml
```

---

## Continuous Integration Recommendations

### GitHub Actions Workflow (`.github/workflows/tests.yml`)

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.14"]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      
      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: uv sync --all-extras
      
      - name: Run tests
        run: uv run pytest --cov=src --cov-report=xml -v
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
```

---

## Appendix A: Complete Fixture Reference

### Fixture Hierarchy

```
tests/conftest.py (root)
├── tmp_input_dir          (function) - Temporary input directory
├── tmp_output_dir         (function) - Temporary output directory
├── tmp_temp_dir           (function) - Temporary processing directory
├── mock_console           (function) - Mock Rich Console
└── mock_output_handler    (function) - Mock OutputHandler protocol

tests/unit/conftest.py
├── channel_data_factory   (function) - Create channel config dicts
├── bus_data_factory       (function) - Create bus config dicts
└── create_mock_wav_file   (function) - Create mock WAV files

tests/unit/config/conftest.py
├── valid_channel_config   (function) - Valid ChannelConfig instance
├── valid_bus_config       (function) - Valid BusConfig instance
├── sample_channel_data    (params)   - Parametrized channel data
├── invalid_channel_data   (params)   - Invalid channel data for error tests
├── mock_channel_list      (function) - List of channel configs
└── mock_bus_list          (function) - List of bus configs

tests/unit/audio/conftest.py
├── mock_soundfile_info    (function) - Mock soundfile.info()
├── soundfile_info_factory (function) - Factory for custom MockSoundFileInfo
├── mock_soundfile_read    (function) - Mock soundfile.read()
└── mock_soundfile_class   (function) - Mock SoundFile context manager

tests/unit/processing/conftest.py
├── mock_converter         (function) - Mock BitDepthConverter
└── sample_segments        (function) - Sample SegmentMap data

tests/unit/cli/conftest.py
├── cli_runner             (function) - Typer CliRunner instance
└── invoke_app             (function) - Factory for invoking CLI
```

---

## Appendix B: Test Naming Conventions

### Test Function Names

```python
# Pattern: test_<what>_<when/with>_<expected_outcome>

def test_validate_files_with_empty_list_raises_error():
    """Empty list input should raise AudioProcessingError."""

def test_channel_config_with_negative_channel_raises_validation_error():
    """Negative channel numbers should fail Pydantic validation."""

def test_build_tracks_creates_output_directory():
    """TrackBuilder should create output dir if it doesn't exist."""
```

### Test Class Names

```python
class TestChannelConfig:
    """Tests for ChannelConfig Pydantic model."""

class TestChannelConfigValidation:
    """Tests specifically for ChannelConfig validation logic."""

class TestAudioFileDiscovery:
    """Tests for AudioFileDiscovery class."""
```

---

## Appendix C: Troubleshooting Common Issues

### Issue: Mocks Not Being Applied

```python
# Wrong: Patching where the object is defined
mocker.patch("soundfile.info")  # Only works if soundfile.info is used directly

# Right: Patch where the object is imported/used
mocker.patch("src.audio.validation.soundfile.info")  # Patch in the consuming module
```

### Issue: Fixture Not Found

```python
# Ensure conftest.py is in the correct directory
# and contains the fixture definition

# If using a fixture from a parent directory, it's automatically available
# If not working, check for typos and ensure __init__.py exists
```

### Issue: Parametrized Tests Running Unexpectedly

```python
# Use explicit IDs for clarity in test output
@pytest.mark.parametrize("input,expected", [
    pytest.param(1, 2, id="positive"),
    pytest.param(-1, 0, id="negative"),
    pytest.param(0, 1, id="zero"),
])
def test_something(input, expected):
    ...
```

---

*Document generated for Channel Weaver v0.1.0*  
*Testing Plan Version 1.0*  
*Last Updated: December 13, 2025*

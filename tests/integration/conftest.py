"""Integration test configuration and fixtures."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Generator

import numpy as np
import pytest
import soundfile as sf



@pytest.fixture(scope="session")
def integration_temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for integration tests."""
    temp_dir = Path(tempfile.mkdtemp(prefix="channel_weaver_integration_"))
    yield temp_dir
    # Cleanup after all tests
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_audio_files(integration_temp_dir: Path) -> Generator[dict[str, Path], None, None]:
    """Create sample mono WAV files for testing."""
    audio_dir = integration_temp_dir / "sample_audio"
    audio_dir.mkdir(exist_ok=True)

    files = {}

    # Create 8 mono WAV files (simulating 8-track recording)
    sample_rate = 44100
    duration = 2.0  # 2 seconds
    samples = int(sample_rate * duration)

    for i in range(8):
        filename = audio_dir / f"{i+1:02d}.wav"
        # Create a sine wave with different frequencies for each track
        frequency = 220 * (i + 1)  # 220Hz, 440Hz, 660Hz, etc.
        t = np.linspace(0, duration, samples, False)
        audio_data = 0.5 * np.sin(2 * np.pi * frequency * t).astype(np.float32)

        sf.write(str(filename), audio_data, sample_rate, subtype='FLOAT')
        files[f"track_{i+1}"] = filename

    yield files


@pytest.fixture
def multichannel_wav_file(integration_temp_dir: Path) -> Generator[Path, None, None]:
    """Create a multichannel WAV file for testing."""
    audio_dir = integration_temp_dir / "multichannel"
    audio_dir.mkdir(exist_ok=True)

    filename = audio_dir / "multichannel.wav"
    sample_rate = 44100
    duration = 1.0
    samples = int(sample_rate * duration)

    # Create 8-channel audio data
    channels = 8
    audio_data = np.random.rand(samples, channels).astype(np.float32) * 0.5

    sf.write(str(filename), audio_data, sample_rate, subtype='FLOAT')
    yield filename


@pytest.fixture
def config_file(integration_temp_dir: Path) -> Generator[Path, None, None]:
    """Create a sample configuration file."""
    config_dir = integration_temp_dir / "config"
    config_dir.mkdir(exist_ok=True)

    config_path = config_dir / "config.py"

    config_content = '''
"""Sample configuration for integration testing."""

from src.config.types import ChannelDict, BusDict

# Channel configuration
CHANNELS: list[ChannelDict] = [
    {"ch": 1, "name": "Drums", "action": "BUS"},
    {"ch": 2, "name": "Drums", "action": "BUS"},
    {"ch": 3, "name": "Bass", "action": "BUS"},
    {"ch": 4, "name": "Guitar", "action": "BUS"},
    {"ch": 5, "name": "Guitar"},
    {"ch": 6, "name": "Vocals", "action": "BUS"},
    {"ch": 7, "name": "Keys"},
    {"ch": 8, "name": "Keys"},
]

# Bus configuration
BUSES: list[BusDict] = [
    {
        "file_name": "DrumsBus",
        "type": "STEREO",
        "slots": {"LEFT": 1, "RIGHT": 2},
    },
    {
        "file_name": "Instruments",
        "type": "STEREO", 
        "slots": {"LEFT": 3, "RIGHT": 4},
    },
    {
        "file_name": "VocalsBus",
        "type": "STEREO",
        "slots": {"LEFT": 6, "RIGHT": 6},
    },
]
'''

    config_path.write_text(config_content)
    yield config_path


@pytest.fixture
def output_dir(integration_temp_dir: Path) -> Path:
    """Create an output directory for test results."""
    output = integration_temp_dir / "output"
    output.mkdir(exist_ok=True)
    return output


@pytest.fixture
def temp_processing_dir(integration_temp_dir: Path) -> Path:
    """Create a temporary processing directory."""
    temp_dir = integration_temp_dir / "temp"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir

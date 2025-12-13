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
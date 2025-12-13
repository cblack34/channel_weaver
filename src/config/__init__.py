"""Configuration package for Channel Weaver."""

# Re-export enums
from src.config.enums import ChannelAction, BusSlot, BusType, BitDepth

# Re-export models
from src.config.models import ChannelConfig, BusConfig

# Re-export validators
from src.config.validators import ChannelValidator, BusValidator

# Re-export loader
from src.config.loader import ConfigLoader

# Re-export defaults
from src.config.defaults import CHANNELS, BUSES

# Re-export types
from src.config.types import SegmentMap, ChannelData, BusData, AudioInfo, ChannelDict, BusDict

__all__ = [
    # Enums
    "ChannelAction",
    "BusSlot",
    "BusType",
    "BitDepth",
    # Models
    "ChannelConfig",
    "BusConfig",
    # Validators
    "ChannelValidator",
    "BusValidator",
    # Loader
    "ConfigLoader",
    # Defaults
    "CHANNELS",
    "BUSES",
    # Types
    "SegmentMap",
    "ChannelData",
    "BusData",
    "AudioInfo",
    "ChannelDict",
    "BusDict",
]
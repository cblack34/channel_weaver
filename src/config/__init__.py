"""Configuration package for Channel Weaver."""

# Re-export enums
from .enums import ChannelAction, BusSlot, BusType, BitDepth

# Re-export models
from .models import ChannelConfig, BusConfig

# Re-export validators
from .validators import ChannelValidator, BusValidator

# Re-export loader
from .loader import ConfigLoader

# Re-export defaults
from .defaults import CHANNELS, BUSES

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
]
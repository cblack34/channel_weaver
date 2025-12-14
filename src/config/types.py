"""Type aliases for Channel Weaver."""
from pathlib import Path
from typing import TypedDict

from src.config.enums import ChannelAction, BusSlot, BusType

type SegmentMap = dict[int, list[Path]]
type ChannelData = ChannelDict
type BusData = BusDict
type AudioInfo = tuple[int, int, str]  # (sample_rate, channels, subtype)


class ChannelDict(TypedDict, total=False):
    """TypedDict for channel configuration dictionaries."""
    ch: int
    name: str
    action: str | ChannelAction
    output_ch: int


class BusDict(TypedDict, total=False):
    """TypedDict for bus configuration dictionaries."""
    file_name: str
    type: str | BusType
    slots: dict[str | BusSlot, int]
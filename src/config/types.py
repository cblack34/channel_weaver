"""Type aliases for Channel Weaver."""
from pathlib import Path
from typing import TypedDict

type SegmentMap = dict[int, list[Path]]
type ChannelData = dict[str, object]
type BusData = dict[str, object]
type AudioInfo = tuple[int, int, str]  # (sample_rate, channels, subtype)


class ChannelDict(TypedDict, total=False):
    """TypedDict for channel configuration dictionaries."""
    ch: int
    name: str
    action: str
    output_ch: int


class BusDict(TypedDict, total=False):
    """TypedDict for bus configuration dictionaries."""
    file_name: str
    type: str
    slots: dict[str, int]
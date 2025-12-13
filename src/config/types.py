"""Type aliases for Channel Weaver."""
from pathlib import Path
from typing import TypeAlias, TypedDict

SegmentMap: TypeAlias = dict[int, list[Path]]
ChannelData: TypeAlias = dict[str, object]
BusData: TypeAlias = dict[str, object]
AudioInfo: TypeAlias = tuple[int, int, str]  # (sample_rate, channels, subtype)


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
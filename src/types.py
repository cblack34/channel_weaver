"""Type aliases for Channel Weaver."""
from pathlib import Path
from typing import TypeAlias

SegmentMap: TypeAlias = dict[int, list[Path]]
ChannelData: TypeAlias = dict[str, object]
BusData: TypeAlias = dict[str, object]
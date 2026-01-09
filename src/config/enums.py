"""Configuration enums for Channel Weaver."""

from enum import Enum, auto


class ChannelAction(Enum):
    """Possible actions that can be taken for a channel."""

    PROCESS = auto()
    BUS = auto()
    SKIP = auto()
    CLICK = auto()


class BusSlot(Enum):
    """Slot positions for stereo buses."""

    LEFT = auto()
    RIGHT = auto()


class BusType(Enum):
    """Supported bus types."""

    STEREO = auto()

    def required_slots(self) -> set[BusSlot]:
        """Return the set of slots required for this bus type."""

        if self is BusType.STEREO:
            return {BusSlot.LEFT, BusSlot.RIGHT}
        raise ValueError(f"Unsupported BusType: {self}")


class BitDepth(str, Enum):
    """Selectable bit depths for output files."""

    SOURCE = "source"
    FLOAT32 = "32float"
    INT24 = "24"
    INT16 = "16"

    def __str__(self) -> str:  # pragma: no cover - convenience for Typer display
        return self.value
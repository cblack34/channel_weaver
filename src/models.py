"""Data models for Channel Weaver configuration."""

from enum import Enum, auto
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class ChannelAction(Enum):
    """Possible actions that can be taken for a channel."""

    PROCESS = auto()
    BUS = auto()
    SKIP = auto()


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


class ChannelConfig(BaseModel):
    """User-editable channel configuration entry."""

    ch: int = Field(..., ge=1, description="Channel number (1-based)")
    name: str
    action: ChannelAction = ChannelAction.PROCESS

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: ChannelAction) -> ChannelAction:  # noqa: B902
        return value


class BusConfig(BaseModel):
    """User-editable bus configuration entry."""

    file_name: str = Field(..., description="Custom file name for output, e.g., '07_overheads'")
    type: BusType = BusType.STEREO
    slots: dict[BusSlot, int] = Field(..., description="Slot to channel mapping")

    @model_validator(mode='after')
    def validate_slots(self) -> Self:  # noqa: B902
        required = self.type.required_slots()
        if set(self.slots.keys()) != required:
            required_slots = ", ".join(slot.name for slot in sorted(required, key=lambda s: s.name))
            raise ValueError(f"{self.type.name} buses require slots: {required_slots}")
        return self
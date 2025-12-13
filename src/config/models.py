"""Pydantic models for Channel Weaver configuration."""

from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.config.enums import ChannelAction, BusSlot, BusType


class ChannelConfig(BaseModel):
    """User-editable channel configuration entry."""

    ch: int = Field(..., ge=1, description="Channel number (1-based)")
    name: str
    action: ChannelAction = ChannelAction.PROCESS
    output_ch: int | None = Field(None, ge=1, description="Output channel number for filename, defaults to ch")

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        """Clean the name by trimming whitespace and replacing spaces with underscores."""
        return value.strip().replace(" ", "_")

    @field_validator("action", mode="before")
    @classmethod
    def validate_action(cls, value) -> ChannelAction:
        if isinstance(value, str):
            try:
                return ChannelAction[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid action: {value}")
        return value

    @model_validator(mode="after")
    def set_default_output_ch(self) -> Self:
        if self.output_ch is None:
            self.output_ch = self.ch
        return self


class BusConfig(BaseModel):
    """User-editable bus configuration entry."""

    file_name: str = Field(..., description="Custom file name for output, e.g., '07_overheads'")
    type: BusType = BusType.STEREO
    slots: dict[BusSlot, int] = Field(..., description="Slot to channel mapping")

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, value) -> BusType:
        if isinstance(value, str):
            try:
                return BusType[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid bus type: {value}")
        return value

    @field_validator("slots", mode="before")
    @classmethod
    def validate_slots_keys(cls, value) -> dict[BusSlot, int]:
        if isinstance(value, dict):
            converted = {}
            for k, v in value.items():
                if isinstance(k, str):
                    try:
                        converted[BusSlot[k.upper()]] = v
                    except KeyError:
                        raise ValueError(f"Invalid bus slot: {k}")
                else:
                    converted[k] = v
            return converted
        return value

    @model_validator(mode='after')
    def validate_slots(self) -> Self:  # noqa: B902
        # Validate slot channel numbers are positive
        for slot, ch in self.slots.items():
            if ch < 1:
                raise ValueError(f"Slot {slot.name} channel must be >= 1, got {ch}")
        # Validate required slots
        required = self.type.required_slots()
        if set(self.slots.keys()) != required:
            required_slots = ", ".join(slot.name for slot in sorted(required, key=lambda s: s.name))
            raise ValueError(f"{self.type.name} buses require slots: {required_slots}")
        return self
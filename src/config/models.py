"""Pydantic models for Channel Weaver configuration."""

from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.config.enums import ChannelAction, BusSlot, BusType


class ProcessingOptions(BaseModel):
    """CLI options that can override configuration values."""

    section_by_click: bool = Field(default=False, description="Enable section splitting by click track")
    gap_threshold_seconds: float | None = Field(default=None, gt=0, description="Override gap threshold for section splitting")
    session_json_path: Path | None = Field(default=None, description="Path to output session JSON metadata")


class SectionSplittingConfig(BaseModel):
    """Configuration for click-based section splitting."""

    enabled: bool = Field(default=False, description="Enable click-based section splitting")
    gap_threshold_seconds: float = Field(default=3.0, gt=0, description="Minimum gap between sections in seconds")
    min_section_length_seconds: float = Field(default=15.0, gt=0, description="Minimum length for a section in seconds")
    bpm_change_threshold: int = Field(default=1, ge=1, description="Minimum BPM change to trigger new section")

    # Algorithm parameters - not configurable via CLI
    bandpass_low: int = Field(default=20, ge=1, description="Low cutoff for click frequency range (Hz)")
    bandpass_high: int = Field(default=20000, ge=1, description="High cutoff for click frequency range (Hz)")

    filter_order: int = Field(default=4, ge=1, description="Butterworth filter order")
    min_peak_distance: float = Field(default=0.1, gt=0, description="Minimum distance between peaks (seconds)")
    peak_prominence: float = Field(default=0.001, gt=0, description="Minimum peak prominence")
    novelty_window: float = Field(default=0.05, gt=0, description="Window size for envelope smoothing (seconds)")

    bpm_window_seconds: float = Field(default=5.0, gt=0, description="Window for BPM estimation (seconds)")
    min_bpm: int = Field(default=45, ge=1, description="Minimum expected BPM")
    max_bpm: int = Field(default=300, ge=1, description="Maximum expected BPM")


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
    def validate_slots(self) -> Self:
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
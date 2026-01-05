"""Pydantic models for click track analysis."""

from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.audio.click.enums import SectionType


class SectionInfo(BaseModel):
    """Information about a detected audio section."""

    section_number: int = Field(..., ge=1, description="Sequential section number (1-based)")
    start_sample: int = Field(..., ge=0, description="Start position in samples")
    end_sample: int = Field(..., ge=0, description="End position in samples")
    section_type: SectionType = Field(..., description="Type of section (song or speaking)")
    bpm: int | None = Field(None, ge=1, description="Estimated BPM for the section")

    @field_validator("section_type", mode="before")
    @classmethod
    def validate_section_type(cls, value) -> SectionType:
        if isinstance(value, str):
            try:
                return SectionType[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid section type: {value}")
        return value

    def get_start_seconds(self, sample_rate: int) -> float:
        """Get start time in seconds."""
        return self.start_sample / sample_rate

    def get_duration_seconds(self, sample_rate: int) -> float:
        """Get duration in seconds."""
        return (self.end_sample - self.start_sample) / sample_rate

    @model_validator(mode="after")
    def validate_sample_range(self) -> Self:
        """Ensure end_sample is after start_sample."""
        if self.end_sample <= self.start_sample:
            raise ValueError(f"end_sample ({self.end_sample}) must be greater than start_sample ({self.start_sample})")
        return self


class SectionBoundaries(BaseModel):
    """Container for a list of section boundaries with helper methods."""

    sections: list[SectionInfo] = Field(default_factory=list, description="List of detected sections")

    def add_section(self, section: SectionInfo) -> None:
        """Add a section to the boundaries."""
        self.sections.append(section)

    def get_section_count(self) -> int:
        """Get the total number of sections."""
        return len(self.sections)

    def get_sections_by_type(self, section_type: SectionType) -> list[SectionInfo]:
        """Get all sections of a specific type."""
        return [s for s in self.sections if s.section_type == section_type]

    def get_total_duration_samples(self) -> int:
        """Get the total duration covered by all sections in samples."""
        if not self.sections:
            return 0
        return max(s.end_sample for s in self.sections) - min(s.start_sample for s in self.sections)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "SectionBoundaries":
        """Create from dictionary representation."""
        return cls.model_validate(data)
"""Enums for click track analysis."""

from enum import Enum


class SectionType(Enum):
    """Types of sections that can be identified in audio."""

    SONG = "song"
    SPEAKING = "speaking"
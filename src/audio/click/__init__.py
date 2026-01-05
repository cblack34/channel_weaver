"""Click track analysis package."""

from src.audio.click.enums import SectionType
from src.audio.click.models import SectionBoundaries, SectionInfo
from src.audio.click.protocols import ClickAnalyzerProtocol

__all__ = [
    "ClickAnalyzerProtocol",
    "SectionBoundaries",
    "SectionInfo",
    "SectionType",
]
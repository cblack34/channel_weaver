"""Click track analysis package."""

from src.audio.click.analyzer import ScipyClickAnalyzer
from src.audio.click.enums import SectionType
from src.audio.click.models import SectionBoundaries, SectionInfo
from src.audio.click.protocols import ClickAnalyzerProtocol
from src.audio.click.section_processor import SectionProcessor

__all__ = [
    "ClickAnalyzerProtocol",
    "ScipyClickAnalyzer",
    "SectionBoundaries",
    "SectionInfo",
    "SectionProcessor",
    "SectionType",
]
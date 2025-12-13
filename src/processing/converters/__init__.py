"""Bit depth conversion strategies."""
from src.processing.converters.protocols import BitDepthConverter
from src.processing.converters.factory import get_converter

__all__ = ["BitDepthConverter", "get_converter"]
"""Factory functions for bit depth converters."""

from typing import cast

from src.config import BitDepth
from src.processing.converters.protocols import BitDepthConverter
from src.processing.converters.float32 import Float32Converter
from src.processing.converters.int24 import Int24Converter
from src.processing.converters.int16 import Int16Converter
from src.processing.converters.source import SourceConverter


def get_converter(bit_depth: BitDepth) -> BitDepthConverter:
    """Factory function to get appropriate converter for the given bit depth.

    Args:
        bit_depth: The target bit depth

    Returns:
        BitDepthConverter: The appropriate converter instance
    """
    converters = {
        BitDepth.FLOAT32: Float32Converter(),
        BitDepth.INT24: Int24Converter(),
        BitDepth.INT16: Int16Converter(),
        BitDepth.SOURCE: SourceConverter(),
    }
    return cast(BitDepthConverter, converters[bit_depth])


def resolve_bit_depth(requested: BitDepth, source: BitDepth | None) -> BitDepth:
    """Return an actionable bit depth, replacing SOURCE with source.

    Args:
        requested: The requested bit depth
        source: The source bit depth (if known)

    Returns:
        BitDepth: The resolved bit depth

    Raises:
        ValueError: If SOURCE is requested but source is None
    """
    if requested is BitDepth.SOURCE:
        if source is None:
            raise ValueError("Cannot resolve source bit depth before validating input files.")
        return source
    return requested
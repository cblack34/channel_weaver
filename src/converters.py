"""Bit depth conversion strategies for Channel Weaver."""

from typing import Protocol

import numpy as np

from src.models import BitDepth


class BitDepthConverter(Protocol):
    """Protocol for bit depth conversion strategies."""

    @property
    def soundfile_subtype(self) -> str:
        """Return the SoundFile subtype string for this bit depth."""
        ...

    @property
    def numpy_dtype(self) -> np.dtype:
        """Return the NumPy dtype for this bit depth."""
        ...

    def convert(self, data: np.ndarray) -> np.ndarray:
        """Convert floating-point audio data to this bit depth."""
        ...


class Float32Converter:
    """Converter for 32-bit float output."""

    @property
    def soundfile_subtype(self) -> str:
        return "FLOAT"

    @property
    def numpy_dtype(self) -> np.dtype:
        return np.float32

    def convert(self, data: np.ndarray) -> np.ndarray:
        """Convert to 32-bit float (no-op for already normalized float data)."""
        return data.astype(np.float32, copy=False)


class Int24Converter:
    """Converter for 24-bit integer output."""

    @property
    def soundfile_subtype(self) -> str:
        return "PCM_24"

    @property
    def numpy_dtype(self) -> np.dtype:
        return np.int32

    def convert(self, data: np.ndarray) -> np.ndarray:
        """Convert to 24-bit integer range."""
        float_data = data.astype(np.float32, copy=False)
        # Scale to 24-bit signed integer range: [-2^23, 2^23-1] = [-8388608, 8388607]
        scaled = np.clip(np.rint(float_data * 8388608.0), -8388608, 8388607)
        return scaled.astype(np.int32)


class Int16Converter:
    """Converter for 16-bit integer output."""

    @property
    def soundfile_subtype(self) -> str:
        return "PCM_16"

    @property
    def numpy_dtype(self) -> np.dtype:
        return np.int16

    def convert(self, data: np.ndarray) -> np.ndarray:
        """Convert to 16-bit integer range."""
        float_data = data.astype(np.float32, copy=False)
        # Scale to 16-bit signed integer range: [-2^15, 2^15-1] = [-32768, 32767]
        scaled = np.clip(np.rint(float_data * 32767.0), -32768, 32767)
        return scaled.astype(np.int16)


class SourceConverter:
    """Converter for source bit depth (preserves original bit depth as 32-bit PCM)."""

    @property
    def bit_depth(self) -> BitDepth:
        return BitDepth.SOURCE

    @property
    def soundfile_subtype(self) -> str:
        return "PCM_32"  # 32-bit signed integer

    @property
    def numpy_dtype(self) -> np.dtype:
        return np.int32

    def convert(self, data: np.ndarray) -> np.ndarray:
        """Convert float32 data to 32-bit signed integer range."""
        float_data = data.astype(np.float32, copy=False)
        # Scale to 32-bit signed integer range: [-2^31, 2^31-1]
        scaled = np.clip(np.rint(float_data * 2147483648.0), -2147483648, 2147483647)
        return scaled.astype(np.int32)


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
    return converters[bit_depth]

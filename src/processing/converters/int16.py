"""16-bit integer converter for Channel Weaver."""

import numpy as np

from src.processing.converters.protocols import BitDepthConverter


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
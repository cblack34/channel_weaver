"""Source bit depth converter for Channel Weaver."""

import numpy as np

from src.config import BitDepth
from src.processing.converters.protocols import BitDepthConverter


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
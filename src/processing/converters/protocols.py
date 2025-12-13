"""Bit depth converter protocols for Channel Weaver."""

from typing import Protocol

import numpy as np


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
"""Output handling package for Channel Weaver."""
from .protocols import OutputHandler
from .console import ConsoleOutputHandler

__all__ = [
    "OutputHandler",
    "ConsoleOutputHandler",
]
"""Output handling package for Channel Weaver."""
from src.output.protocols import OutputHandler
from src.output.console import ConsoleOutputHandler

__all__ = [
    "OutputHandler",
    "ConsoleOutputHandler",
]
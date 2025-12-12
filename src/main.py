"""Entry point for the Midas M32 multitrack processor CLI.

This module exposes a Typer-powered command-line interface that wires editable
channel and bus definitions into a validated configuration object and prepares
paths for downstream processing.
"""
from __future__ import annotations

from src.cli.app import app


if __name__ == "__main__":
    app()

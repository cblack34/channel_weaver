"""CLI application definition for Channel Weaver."""

import typer

from src.cli.commands import main

app = typer.Typer(add_completion=False, help="Midas M32 multitrack processor")

# Register the main command
app.command()(main)
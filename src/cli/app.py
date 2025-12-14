"""CLI application definition for Channel Weaver."""

import typer

from src.cli.commands import process, init_config, validate_config

app = typer.Typer(
    add_completion=False,
    help="Multitrack audio processor - process and organize live recordings.",
    no_args_is_help=True,
)

# Register commands
app.command(name="process", help="Process multitrack recordings")(process)
app.command(name="init-config", help="Generate an example configuration file")(init_config)
app.command(name="validate-config", help="Validate a configuration file")(validate_config)
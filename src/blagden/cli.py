"""Command-line interface for Blagden."""

import typer

from blagden import __version__

app = typer.Typer(
    name="blagden",
    help="Heat intelligence for runners in the tropics. Training insight, not medical advice.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main() -> None:
    """Blagden command-line tools."""


@app.command()
def version() -> None:
    """Print the Blagden version."""
    typer.echo(__version__)

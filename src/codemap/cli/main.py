"""Main CLI application for ContextCurator."""

import logging
from typing import Annotated

import typer

from codemap import __version__
from codemap.cli.commands.hooks import install_hook_command, uninstall_hook_command
from codemap.cli.commands.init import init_command
from codemap.cli.commands.status import status_command
from codemap.cli.commands.update import update_command

app = typer.Typer(
    name="curator",
    help="ContextCurator - Semantic code mapping tool",
    no_args_is_help=True,
)

# -- Core commands -----------------------------------------------------------
app.command("init")(init_command)
app.command("update")(update_command)
app.command("status")(status_command)

# -- Hook commands -----------------------------------------------------------
app.command("install-hook")(install_hook_command)
app.command("uninstall-hook")(uninstall_hook_command)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"curator {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Enable verbose logging"),
    ] = False,
) -> None:
    """ContextCurator - Semantic code mapping tool."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


if __name__ == "__main__":
    app()

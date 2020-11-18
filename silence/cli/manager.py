import argparse
import sys

from silence import __version__
from silence.cli.commands import run, createdb, new

###############################################################################
# Command line interface manager
# It provides the entry point for the 'silence' command.
###############################################################################

HANDLERS = {
    "run": run.handle,
    "createdb": createdb.handle,
    "new": new.handle
}

def run_from_command_line():
    parser = argparse.ArgumentParser(
        description="Silence: An educational framework for deploying RESTful APIs and Web applications."
    )
    
    # Force the user to select one of the available commands,
    # and allow them to provide additional options after it.
    parser.add_argument("-v", "--version", action="version", version=f"Silence v{__version__}")
    parser.add_argument("command", choices=["run", "createdb", "new"])
    parser.add_argument("options", nargs="*")

    # Show the help dialog if the command is issued without any arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    HANDLERS[args.command.lower()](args.options)

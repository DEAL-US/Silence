import argparse
import sys

from silence import __version__
from silence.cli.commands import run, createdb, new, list_templates
from silence.settings import settings

###############################################################################
# Command line interface manager
# It provides the entry point for the 'silence' command.
###############################################################################

HANDLERS = {
    "run": run.handle,
    "createdb": createdb.handle,
    "new": new.handle,
    "list-templates": list_templates.handle
}

def run_from_command_line():
    parser = argparse.ArgumentParser(
        description="Silence: An educational framework for deploying RESTful APIs and Web applications."
    )
    subparsers = parser.add_subparsers(help="sub-command help", dest="command")
    
    # Force the user to select one of the available commands,
    # and allow them to provide additional options after it.
    parser.add_argument("-v", "--version", action="version", version=f"Silence v{__version__}")

    parser_list = subparsers.add_parser("list-templates", help="Lists the available project templates")
    
    parser_new = subparsers.add_parser("new", help="Creates a new project")
    parser_new.add_argument("name", help="The new project's name")
    group = parser_new.add_mutually_exclusive_group()
    group.add_argument("--template", help="Template name to use when creating the new project")
    group.add_argument("--url", help="URL to a Git repo containing a project to clone")
    group.add_argument("--blank", action="store_true", help="Alias to --template blank")

    parser_createdb = subparsers.add_parser("createdb", help="Runs the provided SQL scripts in the adequate order in the database")
    parser_run = subparsers.add_parser("run", help="Starts the web server")

    # Show the help dialog if the command is issued without any arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # Show silence new's help dialog if it was called without any arguments
    if sys.argv[1].lower() == "new" and len(sys.argv) == 2:
        parser_new.print_help()
        sys.exit(1)

    args = parser.parse_args()
    command = args.command.lower()
    HANDLERS[command](args)

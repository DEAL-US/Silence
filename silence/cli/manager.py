import argparse
import logging
import sys

from silence import __version__
from silence.settings import settings
from silence.logging.default_logger import logger
from silence.cli.commands import run, new, list_templates, test

###############################################################################
# Command line interface: the entry point of the 'silence' command.
###############################################################################

HANDLERS = {
    "new": new.handle,
    "run": run.handle,
    "test": test.handle,
    "list-templates": list_templates.handle,
}

def run_from_command_line():
    parser = argparse.ArgumentParser(
        description="Silence: an educational framework for RESTful APIs and web applications."
    )
    parser.add_argument("-v", "--version", action="version", version=f"Silence v{__version__}")
    subparsers = parser.add_subparsers(dest="command")

    p_new = subparsers.add_parser("new", help="Creates a new project")
    p_new.add_argument("name", help="The new project's name (and folder)")
    group = p_new.add_mutually_exclusive_group()
    group.add_argument("--template", help="Template: ez-ui (default), bootstrap or blank")
    group.add_argument("--url", help="URL of a GitHub repo with a project to use as template")
    group.add_argument("--blank", action="store_const", const="blank", dest="template",
                       help="Alias of --template blank")

    p_run = subparsers.add_parser("run", help="Starts the API, the web app and the admin panel")
    p_run.add_argument("--port", type=int, help="HTTP port (by default, the project's)")
    p_run.add_argument("--no-browser", action="store_true", help="Do not open the admin panel")

    p_test = subparsers.add_parser("test", help="Runs the project's tests (tests/*.json)")
    p_test.add_argument("names", nargs="*", help="Run only these tests")

    subparsers.add_parser("list-templates", help="Lists the available project templates")

    for p in subparsers.choices.values():
        p.add_argument("--debug", action="store_true", help="Enables the debug mode")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    if getattr(args, "debug", False):
        settings.DEBUG_ENABLED = True
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    HANDLERS[args.command](args)

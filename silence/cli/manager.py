import argparse
import logging
import sys

from silence import __version__
from silence.settings import settings
from silence.logging.default_logger import logger
from silence.cli.commands import run, new, list_templates, generate, admin, createdb

###############################################################################
# Command line interface: the entry point of the 'silence' command.
###############################################################################

def run_from_command_line():
    parser = argparse.ArgumentParser(
        description="Silence: an educational framework for RESTful APIs and web applications."
    )
    parser.add_argument("-v", "--version", action="version", version=f"Silence v{__version__}")
    subparsers = parser.add_subparsers(dest="command")

    p = subparsers.add_parser("new", help="Creates a new project")
    p.add_argument("name", help="The new project's name (and folder)")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--template", help="Template of the frontend (silence list-templates): ez-ui by default")
    group.add_argument("--url", help="URL of a GitHub repo with a project to use as template")
    group.add_argument("--blank", action="store_const", const="blank", dest="template",
                       help="Alias of --template blank")
    admin_group = p.add_mutually_exclusive_group()
    admin_group.add_argument("--no-admin", action="store_true", help="Without the admin panel")
    admin_group.add_argument("--admin", help="Another admin panel: owner/repo or its GitHub URL")
    p.add_argument("--admin-version", help="Version (git tag) of the admin panel, or latest (the latest tag)")
    p.set_defaults(handler=new.handle)

    p = subparsers.add_parser("run", help="Starts the API, the web app and the admin panel")
    p.add_argument("--port", type=int, help="HTTP port (by default, the project's)")
    p.add_argument("--no-browser", action="store_true", help="Do not open the admin panel")
    p.set_defaults(handler=run.handle)

    p = subparsers.add_parser("createdb", help="Creates the database again with the scripts of sql/ (database.scripts)")
    p.set_defaults(handler=createdb.handle)

    p = subparsers.add_parser("createapi", help="Generates the endpoints of the tables (endpoints/auto_<table>.json)")
    p.add_argument("tables", nargs="*", help="Only these tables or views")
    p.set_defaults(handler=generate.createapi)

    p = subparsers.add_parser("hash", help="Prints the argon2 hash of a password")
    p.add_argument("password")
    p.set_defaults(handler=generate.hash_command)

    p = subparsers.add_parser("admin", help="Admin panel of the project")
    p.add_argument("action", choices=["update"], help="update: installs or updates admin/")
    version_group = p.add_mutually_exclusive_group()
    version_group.add_argument("--version", help="Version (git tag) to install")
    version_group.add_argument("--latest", action="store_true", help="The latest published version (the latest tag of its repo)")
    p.add_argument("--repo", help="Another admin panel: owner/repo or its GitHub URL")
    p.set_defaults(handler=admin.handle)

    p = subparsers.add_parser("list-templates", help="Lists the available project templates")
    p.set_defaults(handler=list_templates.handle)

    for sub in subparsers.choices.values():
        sub.add_argument("--debug", action="store_true", help="Enables the debug mode")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    if getattr(args, "debug", False):
        settings.DEBUG_ENABLED = True
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    args.handler(args)

import json
import os
import shutil
import sys

from silence.settings import settings, new_project_data, merge, PROJECT_FILE
from silence.logging.default_logger import logger
from silence.cli.template_downloader import fetch, fetch_url, DownloadError

###############################################################################
# silence new <name> [--template ez-ui|bootstrap|blank | --url <repo>] [--no-admin]
# Creates the project by composing two parts:
#   - the template of the student's frontend (web/...), from the repo
#     silence-template-v3-<template> of IISSI-US (or any repo with --url);
#   - the admin panel (admin/), from the repo silence-admin-panel, unless
#     --no-admin is given.
# Then writes its silence.json, with a new secret key. Nothing else is asked:
# the rest is configured in the admin panel (or editing the files).
###############################################################################

# Files of a template repo that are not copied to the project
NOT_COPIED = {".git", ".github", "README.md", "LICENSE", ".gitkeep"}

GITIGNORE = """# Silence
__pycache__/
.venv/
"""


def copy_template(src, dest):
    os.makedirs(dest, exist_ok=True)
    for elem in os.listdir(src):
        if elem in NOT_COPIED:
            continue
        s, d = os.path.join(src, elem), os.path.join(dest, elem)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*NOT_COPIED))
        else:
            shutil.copy2(s, d)


def install_admin_panel(dest):
    '''Copies the admin/ folder of silence-admin-panel into the project (replacing it)'''
    src = fetch(settings.ADMIN_PANEL_REPO)
    try:
        panel = os.path.join(src, "admin")
        if not os.path.isdir(panel):
            raise DownloadError(f"{settings.ADMIN_PANEL_REPO} has no admin/ folder")
        target = os.path.join(dest, "admin")
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.copytree(panel, target, ignore=shutil.ignore_patterns(".gitkeep"))
        return panel_version(dest)
    finally:
        shutil.rmtree(src, ignore_errors=True)


def panel_version(project_dir):
    path = os.path.join(project_dir, "admin", "panel.json")
    try:
        with open(path, encoding="utf8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_project_file(dest):
    '''silence.json: the template's values (if any) with a new secret key'''
    path = os.path.join(dest, PROJECT_FILE)
    data = new_project_data()
    if os.path.isfile(path):
        with open(path, encoding="utf8") as f:
            data = merge(data, json.load(f))
        data["secret_key"] = new_project_data()["secret_key"]
        data["version"] = new_project_data()["version"]
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


def handle(args):
    name = args.name
    if os.path.exists(name):
        logger.error("A folder named '%s' already exists here.", name)
        sys.exit(1)

    template = (args.template or settings.DEFAULT_TEMPLATE_NAME).lower()
    try:
        src = fetch_url(args.url) if args.url else fetch(settings.TEMPLATE_PREFIX + template)
    except DownloadError as exc:
        logger.error("Cannot get the template: %s", exc)
        sys.exit(1)
    try:
        copy_template(src, name)
    finally:
        shutil.rmtree(src, ignore_errors=True)

    panel = None
    if not args.no_admin:
        try:
            panel = install_admin_panel(name)
        except DownloadError as exc:
            logger.warning("The project has been created without the admin panel: %s. "
                           "Add it later with 'silence admin update'.", exc)

    write_project_file(name)
    for folder in ("endpoints", "tests", "web"):
        os.makedirs(os.path.join(name, folder), exist_ok=True)
    gitignore = os.path.join(name, ".gitignore")
    if not os.path.isfile(gitignore):
        with open(gitignore, "w", encoding="utf8") as f:
            f.write(GITIGNORE)

    source = args.url or f"the template '{template}'"
    with_panel = f" and the admin panel v{panel.get('version', '?')}" if panel else ""
    logger.info("The Silence project '%s' has been created from %s%s.", name, source, with_panel)
    logger.info("Now run:\n\n    cd %s\n    silence run\n", name)
    if panel:
        logger.info("and configure the database in the admin panel.")
    else:
        logger.info("and configure the database in %s.", PROJECT_FILE)

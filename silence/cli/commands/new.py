import json
import os
import shutil
import sys

from silence.settings import new_project_data, merge, PROJECT_FILE
from silence.logging.default_logger import logger
from silence.cli import template_downloader as tpl
from silence.cli.template_downloader import DownloadError

###############################################################################
# silence new <name> [--template ez-ui|blank | --url <repo>]
#                    [--admin <repo>] [--admin-version <v>|latest] [--no-admin]
# Creates the project by composing two parts, at the versions of the index of
# this Silence (templates.json):
#   - the template of the student's frontend (web/...), or any repo with --url;
#   - the admin panel (admin/), the default one or the repo given with --admin,
#     unless --no-admin is given. silence.json records which one ("admin").
# Then writes its silence.json, with a new secret key. Nothing else is asked:
# the rest is configured in the admin panel (or editing the files).
###############################################################################

# Files of a template repo that are not copied to the project
NOT_COPIED = {".git", ".github", "README.md", "LICENSE", ".gitkeep"}

GITIGNORE = """# Silence
__pycache__/
.venv/
admin/logs/
"""
LOGS_IGNORED = "admin/logs/"  # The log of requests (requestlog.py), also if the template has its .gitignore


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


def install_admin_panel(dest, repo, version):
    '''Copies the admin/ folder of the panel's repo at that version into the project (replacing it)'''
    src = tpl.fetch(repo, version)
    try:
        panel = os.path.join(src, "admin")
        if not os.path.isdir(panel):
            raise DownloadError(f"{repo} has no admin/ folder: it is not an admin panel")
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


def write_project_file(dest, admin):
    '''silence.json: the template's values (if any) with a new secret key and the admin panel'''
    path = os.path.join(dest, PROJECT_FILE)
    data = new_project_data()
    if os.path.isfile(path):
        with open(path, encoding="utf8") as f:
            data = merge(data, json.load(f))
        data["secret_key"] = new_project_data()["secret_key"]
        data["version"] = new_project_data()["version"]
    data["admin"] = admin
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


def handle(args):
    name = args.name
    if os.path.exists(name):
        logger.error("A folder named '%s' already exists here.", name)
        sys.exit(1)

    # The frontend
    templates = tpl.index()["templates"]
    template = (args.template or tpl.default_template()).lower()
    if args.url:
        repo, version, source = args.url, tpl.LATEST, args.url
    elif template in templates:
        repo, version = templates[template]["repo"], templates[template]["version"]
        source = f"the template '{template}' {version}"
    else:
        logger.error("Unknown template '%s'. Available: %s (or any repo with --url).",
                     template, ", ".join(templates))
        sys.exit(1)
    try:
        src = tpl.fetch(repo, version)
    except DownloadError as exc:
        logger.error("Cannot get the template: %s", exc)
        sys.exit(1)
    try:
        copy_template(src, name)
    finally:
        shutil.rmtree(src, ignore_errors=True)

    # The admin panel
    admin, panel = None, None
    if not args.no_admin:
        admin = tpl.default_admin()
        if args.admin:
            admin = {"repo": args.admin, "version": args.admin_version or tpl.LATEST}
        elif args.admin_version:
            admin["version"] = args.admin_version
        try:
            panel = install_admin_panel(name, admin["repo"], admin["version"])
        except DownloadError as exc:
            logger.warning("The project has been created without the admin panel: %s. "
                           "Add it later with 'silence admin update'.", exc)
            admin = None

    write_project_file(name, admin)
    for folder in ("endpoints", "tests", "web"):
        os.makedirs(os.path.join(name, folder), exist_ok=True)
    gitignore = os.path.join(name, ".gitignore")
    if not os.path.isfile(gitignore):
        with open(gitignore, "w", encoding="utf8") as f:
            f.write(GITIGNORE)
    else:
        with open(gitignore, encoding="utf8") as f:
            ignored = f.read()
        if LOGS_IGNORED not in ignored.split():
            with open(gitignore, "a", encoding="utf8") as f:
                f.write(("" if ignored.endswith("\n") or not ignored else "\n") + LOGS_IGNORED + "\n")

    with_panel = f" and the admin panel {admin['repo']} {admin['version']}" if admin else ""
    logger.info("The Silence project '%s' has been created from %s%s.", name, source, with_panel)
    logger.info("Now run:\n\n    cd %s\n    silence run\n", name)
    logger.info("and configure the database in %s.", "the admin panel" if panel else PROJECT_FILE)

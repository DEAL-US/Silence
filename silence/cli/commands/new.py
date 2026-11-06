import json
import os
import shutil
import sys

from silence.settings import settings, new_project_data, merge, PROJECT_FILE
from silence.logging.default_logger import logger
from silence.cli.template_downloader import download_repo, DownloadError

###############################################################################
# silence new <name> [--template ez-ui|bootstrap|blank] [--url <repo>]
# Creates the project folder from a template (downloaded from the IISSI-US
# repos, or the copy bundled with Silence if it cannot be downloaded) and
# writes its silence.json. Nothing else is asked: the rest is configured in
# the admin panel.
###############################################################################

BUNDLED = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")

GITIGNORE = """# Silence
__pycache__/
.venv/
"""


def handle(args):
    name = args.name
    if os.path.exists(name):
        logger.error("A folder named '%s' already exists here.", name)
        sys.exit(1)

    if args.url:
        try:
            download_repo(args.url, name)
        except DownloadError as exc:
            logger.error(str(exc))
            sys.exit(1)
        source = args.url
    else:
        template = (args.template or settings.DEFAULT_TEMPLATE_NAME).lower()
        repo = f"https://github.com/{settings.GITHUB_TEMPLATES_OWNER}/{settings.TEMPLATE_PREFIX}{template}"
        try:
            download_repo(repo, name)
            source = repo
        except DownloadError as exc:
            bundled = os.path.join(BUNDLED, template)
            if not os.path.isdir(bundled):
                logger.error("Unknown template '%s' (%s).", template, exc)
                sys.exit(1)
            logger.debug("%s; using the bundled template", exc)
            shutil.copytree(bundled, name)
            source = f"the bundled template '{template}'"

    # silence.json: the template's values (if any) with a new secret key
    path = os.path.join(name, PROJECT_FILE)
    data = new_project_data()
    if os.path.isfile(path):
        with open(path, encoding="utf8") as f:
            data = merge(data, json.load(f))
        data["secret_key"] = new_project_data()["secret_key"]
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")

    for folder in ("endpoints", "tests", "web"):
        os.makedirs(os.path.join(name, folder), exist_ok=True)
    gitignore = os.path.join(name, ".gitignore")
    if not os.path.isfile(gitignore):
        with open(gitignore, "w", encoding="utf8") as f:
            f.write(GITIGNORE)

    logger.info("The Silence project '%s' has been created from %s.", name, source)
    logger.info("Now run:\n\n    cd %s\n    silence run\n\nand configure the database in the admin panel.", name)

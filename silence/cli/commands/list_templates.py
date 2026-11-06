import requests

from silence.settings import settings
from silence.logging.default_logger import logger
from silence.cli.commands.new import BUNDLED
import os


def handle(args):
    prefix = settings.TEMPLATE_PREFIX
    templates = {}
    try:
        url = f"https://api.github.com/orgs/{settings.GITHUB_TEMPLATES_OWNER}/repos?per_page=100"
        for repo in requests.get(url, timeout=10).json():
            name = repo["name"].lower()
            if name.startswith(prefix):
                templates[name[len(prefix):]] = repo.get("description") or ""
    except Exception as exc:
        logger.debug("Cannot query GitHub: %s", exc)

    if os.path.isdir(BUNDLED):
        for name in os.listdir(BUNDLED):
            templates.setdefault(name, "(bundled with Silence)")

    print("Available templates:")
    for name in sorted(templates):
        default = " (default)" if name == settings.DEFAULT_TEMPLATE_NAME else ""
        desc = f": {templates[name]}" if templates[name] else ""
        print(f"    · {name}{default}{desc}")

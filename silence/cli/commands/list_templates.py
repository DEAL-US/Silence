import os

import requests

from silence.settings import settings
from silence.logging.default_logger import logger


def handle(args):
    prefix = settings.TEMPLATE_PREFIX
    templates = {}
    headers = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}
    try:
        url = f"https://api.github.com/orgs/{settings.GITHUB_TEMPLATES_OWNER}/repos?per_page=100&type=all"
        for repo in requests.get(url, headers=headers, timeout=10).json():
            name = repo["name"].lower()
            if name.startswith(prefix):
                templates[name[len(prefix):]] = repo.get("description") or ""
    except Exception as exc:
        logger.error("Cannot query GitHub: %s", exc)

    base = os.environ.get("SILENCE_SOURCES")
    if base and os.path.isdir(os.path.expanduser(base)):
        for name in os.listdir(os.path.expanduser(base)):
            if name.startswith(prefix):
                templates.setdefault(name[len(prefix):], "(local copy)")

    print("Available templates:")
    for name in sorted(templates):
        default = " (default)" if name == settings.DEFAULT_TEMPLATE_NAME else ""
        desc = f": {templates[name]}" if templates[name] else ""
        print(f"    · {name}{default}{desc}")

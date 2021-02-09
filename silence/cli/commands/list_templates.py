from silence.settings import settings
from silence.logging.default_logger import logger

import requests
import traceback
import sys

def handle(args):
    query_url = f"https://api.github.com/orgs/{settings.GITHUB_TEMPLATES_OWNER}/repos"

    try:
        repo_data = requests.get(query_url).json()
    except Exception as exc:
        logger.debug(traceback.format_exc())
        logger.error("An error has occurred when querying GitHub's API to obtain the list of templates.")
        if not settings.DEBUG_ENABLED:
            logger.error("Add --debug to see the full stack trace.")
        sys.exit(1)

    templates = []
    for repo in repo_data:
        name = repo["name"].lower()
        if name.startswith("silence-template"):
            template_name = name.replace("silence-template-", "")
            desc = repo["description"]
            templates.append({"name": template_name, "desc": desc})

    templates.sort(key=lambda x: x["name"])

    print("Available templates:")
    for tmpl in templates:
        name = tmpl["name"]
        default = " (default)" if name == settings.DEFAULT_TEMPLATE_NAME.lower() else ""
        desc = f': {tmpl["desc"]}' if tmpl["desc"] else ""

        print(f"    · {name}{default}{desc}")

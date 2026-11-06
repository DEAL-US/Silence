import io
import re
import shutil
import zipfile
from pathlib import Path

import requests

from silence.logging.default_logger import logger

###############################################################################
# Downloads a project template from a GitHub repo (zip of its default branch).
###############################################################################

RE_REPO_URL = re.compile(r"https?://([^/]+)/([^/]+)/([^/]+)")


class DownloadError(Exception):
    pass


def download_repo(repo_url, dest):
    '''Downloads the repo into dest (which must not exist). Raises DownloadError'''
    repo_url = repo_url.removesuffix("/").removesuffix(".git")
    m = RE_REPO_URL.match(repo_url)
    if not m:
        raise DownloadError(f"Invalid repo URL: {repo_url}")
    host, owner, repo = m.groups()
    if host != "github.com":
        raise DownloadError("Only repos hosted in github.com are supported")

    try:
        api = requests.get(f"https://api.github.com/repos/{owner}/{repo}", timeout=10)
        if api.status_code != 200:
            raise DownloadError(f"Repo {owner}/{repo} not found (or not public)")
        branch = api.json().get("default_branch", "main")
        r = requests.get(f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip", timeout=30)
        r.raise_for_status()
    except requests.RequestException as exc:
        raise DownloadError(f"Cannot download {repo_url}: {exc}")

    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(dest)

    # Everything is inside a <repo>-<branch> folder: move it up
    inner = next(Path(dest).iterdir())
    for elem in inner.iterdir():
        shutil.move(str(elem), dest)
    inner.rmdir()

    for gitkeep in Path(dest).rglob(".gitkeep"):
        gitkeep.unlink()
    logger.debug("Downloaded %s into %s", repo_url, dest)

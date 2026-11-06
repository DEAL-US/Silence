import io
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

from silence.logging.default_logger import logger
from silence.settings import settings

###############################################################################
# Gets a repo of IISSI-US (a template of the student's frontend, or the admin
# panel) as a folder:
#   1. from a local folder, if SILENCE_SOURCES points to a folder that contains
#      it (handy while developing them, or while the repos are private);
#   2. from GitHub: the zip of its default branch (with GITHUB_TOKEN, if set,
#      so that private repos can be downloaded too).
###############################################################################

RE_REPO_URL = re.compile(r"https?://github\.com/([^/]+)/([^/]+)")


class DownloadError(Exception):
    pass


def local_source(repo):
    base = os.environ.get("SILENCE_SOURCES")
    if base:
        path = os.path.join(os.path.expanduser(base), repo)
        if os.path.isdir(path):
            return path
    return None


def download_zip(owner, repo):
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if token:
        url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
    else:
        url = f"https://github.com/{owner}/{repo}/archive/HEAD.zip"
    try:
        r = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as exc:
        raise DownloadError(f"Cannot download {owner}/{repo}: {exc}")
    if r.status_code != 200:
        raise DownloadError(f"Cannot download {owner}/{repo} (HTTP {r.status_code}"
                            + ("; if it is private, set GITHUB_TOKEN)" if not token else ")"))
    return r.content


def fetch(repo, owner=None):
    '''Returns a temporary folder with the contents of the repo (the caller removes it)'''
    owner = owner or settings.GITHUB_TEMPLATES_OWNER
    tmp = tempfile.mkdtemp(prefix="silence-")
    local = local_source(repo)
    if local:
        logger.debug("Using the local copy of %s in %s", repo, local)
        shutil.copytree(local, tmp, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
        return tmp
    content = download_zip(owner, repo)
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        z.extractall(tmp)
    # Everything is inside one folder (<repo>-<branch> or <owner>-<repo>-<sha>): move it up
    inner = next(Path(tmp).iterdir())
    for elem in inner.iterdir():
        shutil.move(str(elem), tmp)
    inner.rmdir()
    return tmp


def fetch_url(url):
    '''Like fetch, for the URL of any GitHub repo (silence new --url)'''
    m = RE_REPO_URL.match(url.removesuffix("/").removesuffix(".git"))
    if not m:
        raise DownloadError(f"Invalid repo URL: {url} (only github.com)")
    return fetch(m.group(2), m.group(1))

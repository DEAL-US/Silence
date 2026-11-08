import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import requests

from silence.logging.default_logger import logger

###############################################################################
# The templates of the student's frontend and the admin panel: the index of
# this version of Silence (templates.json, each one at a fixed version) and
# how to get a repo at a version, as a folder:
#   1. from a local folder, if SILENCE_SOURCES points to a folder that contains
#      it (handy while developing them, or while the repos are private): the
#      git tag of that version, or the working copy for "latest";
#   2. from GitHub: the zip of that tag, or of the default branch for "latest"
#      (with GITHUB_TOKEN, if set, so that private repos can be downloaded).
###############################################################################

INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates.json")
RE_REPO = re.compile(r"^(?:https?://github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
LATEST = "latest"


class DownloadError(Exception):
    pass


def index():
    with open(INDEX_PATH, encoding="utf8") as f:
        return json.load(f)


def default_template():
    templates = index()["templates"]
    return next((n for n, t in templates.items() if t.get("default")), next(iter(templates)))


def default_admin():
    '''{"repo", "version"} of the admin panel of this version of Silence'''
    return dict(index()["admin"])


def parse_repo(text):
    '''"owner/repo" or a GitHub URL -> (owner, repo)'''
    m = RE_REPO.match((text or "").strip())
    if not m:
        raise DownloadError(f"Invalid repo '{text}': use owner/repo or its github.com URL")
    return m.group(1), m.group(2)


def local_source(repo):
    base = os.environ.get("SILENCE_SOURCES")
    if base:
        path = os.path.join(os.path.expanduser(base), repo)
        if os.path.isdir(path):
            return path
    return None


def from_local(path, version, dest):
    if version == LATEST:
        shutil.copytree(path, dest, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
        return
    # The files of that tag (git archive), so that the local copy behaves like GitHub
    try:
        data = subprocess.run(["git", "-C", path, "archive", "--format=zip", version],
                              check=True, capture_output=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise DownloadError(f"The local copy {path} has no version {version} (git tag)")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(dest)


def download_zip(owner, repo, version):
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    ref = "" if version == LATEST else version
    if token:
        url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{ref}".rstrip("/")
    elif version == LATEST:
        url = f"https://github.com/{owner}/{repo}/archive/HEAD.zip"
    else:
        url = f"https://github.com/{owner}/{repo}/archive/refs/tags/{version}.zip"
    try:
        r = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as exc:
        raise DownloadError(f"Cannot download {owner}/{repo}: {exc}")
    if r.status_code != 200:
        hint = "" if token else "; if it is private, set GITHUB_TOKEN"
        raise DownloadError(f"Cannot download {owner}/{repo} {version} (HTTP {r.status_code}{hint})")
    return r.content


def fetch(repo_spec, version=LATEST):
    '''A temporary folder with the repo ("owner/repo" or URL) at that version (the caller removes it)'''
    owner, repo = parse_repo(repo_spec)
    tmp = tempfile.mkdtemp(prefix="silence-")
    try:
        local = local_source(repo)
        if local:
            logger.debug("Using the local copy of %s (%s) in %s", repo, version, local)
            from_local(local, version, tmp)
            return tmp
        with zipfile.ZipFile(io.BytesIO(download_zip(owner, repo, version))) as z:
            z.extractall(tmp)
        # Everything is inside one folder (<repo>-<ref> or <owner>-<repo>-<sha>): move it up
        inner = next(Path(tmp).iterdir())
        for elem in inner.iterdir():
            shutil.move(str(elem), tmp)
        inner.rmdir()
        return tmp
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)  # Nothing is left behind if it cannot be fetched
        raise


def version_key(tag):
    '''A tag ("v1.10.0") as a tuple that sorts by version'''
    return tuple(int(n) for n in re.findall(r"\d+", tag)) or (0,)


def latest_tag(repo_spec):
    '''The latest version (git tag) of a repo: from its local copy (SILENCE_SOURCES) or from GitHub
    (GITHUB_TOKEN for a private one). DownloadError if it cannot be known'''
    owner, repo = parse_repo(repo_spec)
    local = local_source(repo)
    if local:
        try:
            tags = subprocess.run(["git", "-C", local, "tag"], check=True, capture_output=True, text=True).stdout.split()
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise DownloadError(f"The local copy {local} is not a git repo")
    else:
        token = os.environ.get("GITHUB_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            r = requests.get(f"https://api.github.com/repos/{owner}/{repo}/tags?per_page=100", headers=headers, timeout=10)
        except requests.RequestException as exc:
            raise DownloadError(f"Cannot reach GitHub: {exc}")
        if r.status_code != 200:
            hint = "" if token else "; if it is private, set GITHUB_TOKEN"
            raise DownloadError(f"Cannot read the versions of {owner}/{repo} (HTTP {r.status_code}{hint})")
        tags = [t["name"] for t in r.json()]
    if not tags:
        raise DownloadError(f"{owner}/{repo} has no versions (git tags) yet")
    return max(tags, key=version_key)

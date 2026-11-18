import json
import os
import re
from importlib import metadata

import requests

from silence.settings import settings
from silence.logging.default_logger import logger
from silence import __version__

###############################################################################
# Updates of Silence (DEAL-US/Silence#23). Silence 3 is installed from GitHub,
# from the branch "stable" (which points to the latest release, so the same
# command installs and updates it), and also from PyPI once it is published
# there. The latest version is the highest of both: the __version__ of the
# branch stable and the one of PyPI. The command to update is the one of how
# this Silence was installed (pip records it: direct_url.json, PEP 610).
###############################################################################

REPO = "DEAL-US/Silence"
STABLE_ZIP = f"https://github.com/{REPO}/archive/refs/heads/stable.zip"
STABLE_INIT = f"https://raw.githubusercontent.com/{REPO}/stable/silence/__init__.py"
PYPI_JSON = "https://pypi.org/pypi/Silence/json"

UPGRADE = {
    "github": f"pip install --upgrade {STABLE_ZIP}",
    "pypi": "pip install --upgrade silence",
}


def version_key(version):
    '''A version, to compare them: "3.2.0" > "3.2.0rc1" > "3.2.0.dev1" > "3.1.2". Its numbers, and then
    whether it is a final one (a pre-release or development one is older than its final one)'''
    text = str(version).strip().lstrip("vV")
    match = re.match(r"\d+(?:\.\d+)*", text)
    if not match:
        return ()
    numbers = [int(n) for n in match.group(0).split(".")]
    while len(numbers) < 3:
        numbers.append(0)
    rest = text[match.end():].lower()
    m = re.match(r"\.?(a|b|rc|dev)(\d*)", rest)
    if not m:
        stage = (3, 0)  # Final
    else:
        stage = ({"dev": 0, "a": 1, "b": 1, "rc": 2}[m.group(1)], int(m.group(2) or 0))
    return tuple(numbers) + stage


# Kept for the code that imported it: the numbers of a version
def release_tuple(version):
    return version_key(version)[:-2]


def installed_from():
    '''How this Silence was installed: "github" (a URL, e.g., the zip of a tag or of stable),
    "pypi", "editable" (a working copy, pip install -e) or "unknown"'''
    import silence
    # A working copy: its code is not in the packages of Python (site-packages)
    here = os.path.normpath(os.path.dirname(silence.__file__)).split(os.sep)
    if not {"site-packages", "dist-packages"} & set(here):
        return "editable"
    try:
        dist = metadata.distribution("Silence")
    except metadata.PackageNotFoundError:
        return "unknown"
    text = dist.read_text("direct_url.json")
    if not text:
        return "pypi"  # Installed from an index
    try:
        info = json.loads(text)
    except ValueError:
        return "unknown"
    if info.get("dir_info", {}).get("editable"):
        return "editable"
    return "github" if "github.com" in info.get("url", "") else "unknown"


def upgrade_command(source=None):
    '''The command that updates this Silence (None for a working copy, or if it is not known)'''
    return UPGRADE.get(source or installed_from())


def github_version():
    '''The version of the branch stable of the repo (the latest release)'''
    text = requests.get(STABLE_INIT, timeout=5).text
    match = re.search(r"__version__\s*=\s*[\"']([^\"']+)[\"']", text)
    if not match:
        raise ValueError("the branch stable has no __version__")
    return match.group(1)


def pypi_version():
    return requests.get(PYPI_JSON, timeout=5).json()["info"]["version"]


def latest_version():
    '''The latest published version of Silence: the highest of GitHub (stable) and PyPI. An exception
    if neither can be read'''
    found, errors = [], []
    for read in (github_version, pypi_version):
        try:
            found.append(read())
        except Exception as exc:  # The network, a repo without stable yet...
            errors.append(f"{read.__name__}: {exc}")
    if not found:
        raise RuntimeError("; ".join(errors))
    return max(found, key=version_key)


def check_for_new_version():
    '''The latest version, if it is newer than this one (and updates are checked); else False'''
    if not settings.CHECK_FOR_UPDATES:
        return False
    logger.debug("Checking for new updates...")
    try:
        latest = latest_version()
    except Exception as exc:
        logger.debug("Exception occurred when checking for updates (muted): %s", exc)
        return False
    if version_key(latest) > version_key(__version__):
        logger.debug("New version available")
        return latest
    logger.debug("Running latest version")
    return False

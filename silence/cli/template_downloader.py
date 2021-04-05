import re
import zipfile
import requests
import sys

from silence.logging.default_logger import logger

from os import listdir, remove, getcwd
from os.path import join, isfile, isdir, basename
from urllib.parse import urlparse
from shutil import move, rmtree
from secrets import token_urlsafe
from pathlib import Path

RE_REPO_URL = re.compile(r"https?:\/\/(.*?)\/(.*?)\/(.*)")
RE_SECRET_KEY = re.compile(r"""SECRET_KEY\s*=\s*['"]([a-zA-Z0-9-\_=\/+]+)['"]""")

def download_from_github(project_name, repo_url):
    # Check that the current directory does not contain a folder with the same name
    if isdir(project_name):
        logger.error(f"A folder named '{project_name}' already exists in the current directory.")
        sys.exit(1)

    # Remove the trailing .git or slash if they exist
    # We could use .removesuffix, but it was added in 3.9... maybe if we bump
    # the required Python version some time in the future
    suffixes = (".git", "/")
    for suffix in suffixes:
        if repo_url.endswith(suffix):
            repo_url = repo_url[:-len(suffix)]

    # Check that the repo URL is acceptable
    m = RE_REPO_URL.match(repo_url.lower())
    if not m:
        logger.error("Invalid repo URL, please check your spelling and try again.")
        sys.exit(1)

    host, username, repo_name = m.groups()

    # Check that the host is supported
    if host not in ("github.com", "github.eii.us.es"):
        logger.error("Only repos hosted in github.com or github.eii.us.es are supported.")
        sys.exit(1)

    # Download it (this takes care of querying the relevant API to find out
    # how the default branch is called, and exiting if the repo does not exist)
    git_clone(host, username, repo_name, project_name + "/")

    # Unpack it (everything is inside the <name>-<branch> folder)
    branch_folder_name = listdir(project_name)[0]
    
    # Move everything inside that folder outside
    branch_folder = join(project_name, branch_folder_name)
    for elem in listdir(branch_folder):
        move(join(branch_folder, elem), join(project_name, elem))

    # Remove the now empty folder
    rmtree(branch_folder)

    # Look for .gitkeep files and remove them (especially useful in the case
    # of the blank template project)
    for gitkeep_path in Path(project_name).rglob(".gitkeep"):
        remove(gitkeep_path)

    # Read the settings.py file of the downloaded project, removing the existing
    # SECRET_KEY if it exists and creating a new one. Will also raise a warning
    # if the project does not contain a settings.py file.
    settings_path = join(project_name, "settings.py")

    try:
        settings_content = open(settings_path, "r", encoding="utf-8").read()
        secret_key = token_urlsafe(32)

        if "SECRET_KEY" in settings_content:
            # SECRET_KEY already present, overwrite it
            settings_content = RE_SECRET_KEY.sub(f'SECRET_KEY = "{secret_key}"', settings_content)

        else:
            # SECRET_KEY not present, add it with the extra comments
            settings_content += "\n" + \
                "# A random string that is used for security purposes\n" + \
                "# (this has been generated automatically upon project creation)\n" + \
                f'SECRET_KEY = "{secret_key}"\n'

        open(settings_path, "w", encoding="utf-8").write(settings_content)

    except FileNotFoundError:
        logger.warning("The downloaded project does not have a settings.py file " +
         "at its root, it may not be a valid Silence project.")

def git_clone(host, username, repo_name, clone_dir):
    # Get the default branch (we've checked previously that the host is one of
    # the following)
    api_url = {
        "github.com": f"https://api.github.com/repos/{username}/{repo_name}",
        "github.eii.us.es": f"https://github.eii.us.es/api/v3/repos/{username}/{repo_name}"
    }[host]

    api_response = requests.get(api_url)
    if api_response.status_code == 404:
        logger.error("Repo not found")
        sys.exit(1)

    branch = api_response.json()["default_branch"]

    git_url = f"https://{host}/{username}/{repo_name}"
    repo_file = f"{branch}.zip"
    repo_zip = git_url + f"/archive/{repo_file}"

    if isfile(repo_file):
        remove(repo_file)

    fn = basename(urlparse(repo_zip).path)
    zip_path = save(repo_zip, join(getcwd(), fn))

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(clone_dir)

    if isfile(zip_path):
        remove(zip_path)

# Adapted to our needs from https://github.com/x011/dload/
def save(url, path):
    r = requests.get(url)
    with open(path, 'wb') as f:
        f.write(r.content)
    return path

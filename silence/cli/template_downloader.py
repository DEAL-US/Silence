import re
import zipfile
import requests

from os import listdir, remove, getcwd
from os.path import join, isfile, basename
from urllib.parse import urlparse
from shutil import move, rmtree
from secrets import token_urlsafe

# Adapted to our needs from https://github.com/x011/dload/
def save(url, path):
    r = requests.get(url)
    with open(path, 'wb') as f:
        f.write(r.content)
    return path

def git_clone(git_url, clone_dir):
    git_url = git_url.strip()
    repo_name = re.sub(r"\.git$", "", git_url, 0, re.IGNORECASE | re.MULTILINE)
    repo_zip = repo_name + "/archive/master.zip"

    if isfile("master.zip"):
        remove("master.zip")

    fn = basename(urlparse(repo_zip).path)
    zip_path = save(repo_zip, join(getcwd(), fn))

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(clone_dir)

    if isfile(zip_path):
        remove(zip_path)

def download_from_github(project_name, repo_url):
    git_clone(repo_url, project_name + "/")

    # Unpack it (everything is inside the <name>-master folder)
    branch_folder_name = listdir(project_name)[0]
    
    # Move everything inside that folder outside
    branch_folder = join(project_name, branch_folder_name)
    for elem in listdir(branch_folder):
        move(join(branch_folder, elem), join(project_name, elem))

    # Remove the now empty folder
    rmtree(branch_folder)

    # Generate the random string for the Flask secret key
    # and add it to the settings.py file
    secret_key = token_urlsafe(32)

    with open(join(project_name, "settings.py"), "a", encoding="utf-8") as f:
        f.write("\n\n")
        f.write("# A random string that is used for security purposes\n")
        f.write("# (this has been generated automatically upon project creation)\n")
        f.write(f'SECRET_KEY = "{secret_key}"\n')
import dload

from os import listdir
from os.path import join
from shutil import move, rmtree
from secrets import token_urlsafe

def download_from_github(project_name, repo_url):
    dload.git_clone(repo_url, project_name + "/")

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
import importlib

from os import listdir
from os.path import splitext

###############################################################################
# Look for .py files inside the project's "/api" folder
# and force them to run, activating the @endpoint decorators
###############################################################################

def load_user_endpoints():
    # Load every .py file inside the api/ folder
    for pyfile in listdir("api"):
        module_name = "api." + splitext(pyfile)[0]

        try:
            importlib.import_module(module_name)
        except ImportError:
            raise RuntimeError(f"Could not load the API file {module_name}")
    
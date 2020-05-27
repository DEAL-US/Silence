import importlib
import sys
import os

from silence.settings import default_settings

###############################################################################
# A Settings class that contains the default settings as attributes,
# overriding them with the user provided settings when necessary.
###############################################################################

class Settings:
    def __init__(self):
        # Load the default settings
        for setting in dir(default_settings):
            if setting.isupper():
                setattr(self, setting, getattr(default_settings, setting))

        # Override the default settings with the user-defined ones
        try:
            sys.path.append(os.getcwd())
            #importlib.invalidate_caches()
            user_settings = importlib.import_module("settings")

            for setting in dir(user_settings):
                if setting.isupper():
                    setattr(self, setting, getattr(user_settings, setting))
        except ModuleNotFoundError:
            if "run" in sys.argv or "createdb" in sys.argv:
                print("Can't find the settings.py file! Are you running this command from the project's root folder?")
                sys.exit(1)
        
settings = Settings()

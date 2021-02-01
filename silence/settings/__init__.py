import importlib
import pprint
import sys
import os

from silence.settings import default_settings

###############################################################################
# A Settings class that contains the default settings as attributes,
# overriding them with the user provided settings when necessary.
###############################################################################

class Settings:
    def __init__(self):
        self.setting_keys = set()

        # Load the default settings
        for setting in dir(default_settings):
            if setting.isupper():
                self.setting_keys.add(setting)
                setattr(self, setting, getattr(default_settings, setting))

        # Override the default settings with the user-defined ones
        try:
            sys.path.append(os.getcwd())
            user_settings = importlib.import_module("settings")

            for setting in dir(user_settings):
                if setting.isupper():
                    self.setting_keys.add(setting)
                    setattr(self, setting, getattr(user_settings, setting))

            # Ensure that the user has provided a SECRET_KEY
            if not hasattr(self, "SECRET_KEY"):
                print("You need to provide a SECRET_KEY in your settings.py file.")
                print("If you have git clone'd this project, use 'silence new' instead,")
                print("and it will automatically generate a SECRET_KEY for you.")
                sys.exit(1)

        except ModuleNotFoundError:
            if "run" in sys.argv or "createdb" in sys.argv:
                print("Can't find the settings.py file! Are you running this command from the project's root folder?")
                sys.exit(1)

    def __str__(self):
        return pprint.pformat({setting: getattr(self, setting) for setting in self.setting_keys})
        
settings = Settings()

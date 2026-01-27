import importlib
import pprint
import sys
import os

from silence.settings import default_settings

###############################################################################
# A Settings class that contains the default settings as attributes,
# overriding them with the user provided settings when necessary.
###############################################################################

# If you are editing this file, keep this in mind:
# This is imported by many different parts of Silence to read the settings
# of the current project. This means that importing other parts of Silence
# here will most likely result in an error caused by a circular import.
# That's the reason why we can't even import the logger here and we resort
# to print(), because the logger itself needs the settings to be fully loaded
# to configure itself.
# So, try to keep the imports of other Silence modules to a bare minimum in
# the headers of this file. Importing them inside functions is OK, provided
# that they will be called after everything has been loaded

class Settings:
    def __init__(self):
        self.setting_keys = set()
        self.unknown_settings = set()

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
                # If the name of the setting is not known, store it to
                # later warn the user about them (unless it's the SECRET_KEY,
                # which has no default)
                if setting != "SECRET_KEY" and not hasattr(default_settings, setting):
                    self.unknown_settings.add(setting)

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

    def warn_unknown_settings(self):
        from silence.logging.default_logger import logger
        if self.unknown_settings:
            logger.warning("The following parameters in your settings.py are " 
                           "unknown and will be ignored: " + ", ".join(self.unknown_settings))

    def __str__(self):
        return pprint.pformat({setting: getattr(self, setting) for setting in self.setting_keys})
        
settings = Settings()

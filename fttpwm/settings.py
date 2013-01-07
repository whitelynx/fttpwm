from os.path import expanduser, join, dirname, exists
import logging


logger = logging.getLogger("fttpwm.settings")


class Settings(dict):
    __defaultRcFileLocations = (
            expanduser("~/.fttpwmrc.py"),
            "/etc/fttpwmrc.py",
            join(dirname(__file__), "default_fttpwmrc.py")
            )

    __defaultSettings = dict()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return self.__defaultSettings[key]

    def setDefaults(self, **kwargs):
        self.__defaultSettings.update(kwargs)

    def loadSettings(self, filenames=__defaultRcFileLocations):
        #TODO: Instead of just looking for the first settings file in the given locations, we should load all of them,
        # overwriting lower-priority settings with higher-priority ones.
        for filename in filenames:
            if exists(filename):
                settingsFile = filename
                # We've found the settings file; stop looking.
                break

        self.clear()

        execfile(settingsFile, {}, self)


settings = Settings()

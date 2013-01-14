from os.path import join, dirname, exists
import logging

from .xdg.basedir import config as config_dirs


logger = logging.getLogger("fttpwm.settings")


class Settings(dict):
    __defaultConfigFile = join(dirname(__file__), "default_config.py")

    __defaultSettings = dict()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return self.__defaultSettings[key]

    def setDefaults(self, **kwargs):
        self.__defaultSettings.update(kwargs)

    def loadSettings(self):
        logger.info("Loading settings...")
        self.clear()

        # Load each settings file, overwriting lower-priority settings with higher-priority ones.
        for filename in reversed(config_dirs.findAllFiles("fttpwm/config.py") + [self.__defaultConfigFile]):
            if exists(filename):
                # We've found a settings file; load it.
                logger.debug("Found settings file: %s", filename)
                execfile(filename, self)

        logger.info("Finished loading settings.")


settings = Settings()

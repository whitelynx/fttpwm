# -*- coding: utf-8 -*-
"""Colored logger class

Copyright (c) 2011 David H. Bronke and Christopher S. Case
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

# On Windows, try loading colorama.
use_color = True
import platform
if platform.system() == 'Windows':
    try:
        import colorama

        colorama.init()
    except ImportError:
        logging.error("Couldn't import colorama! Disabling color output.")
        use_color = False


class ColoredConsoleHandler(logging.StreamHandler):
    def emit(self, record):
        if use_color:
            # Need to make a actual copy of the record
            # to prevent altering the message for other loggers
            levelno = record.levelno
            if(levelno >= 50):  # CRITICAL / FATAL
                record.levelColor = '\x1b[1;4;35m'  # bold underlined magenta
            elif(levelno >= 40):  # ERROR
                record.levelColor = '\x1b[1;31m'  # red
            elif(levelno >= 30):  # WARNING
                record.levelColor = '\x1b[1;33m'  # yellow
            elif(levelno >= 20):  # INFO
                record.levelColor = '\x1b[1;32m'  # green
            elif(levelno >= 10):  # DEBUG
                record.levelColor = '\x1b[37m'  # white
            else:  # NOTSET and anything else
                record.levelColor = '\x1b[0m'  # normal

            record.bold = '\x1b[1m'
            record.faint = '\x1b[2m'
            record.italic = '\x1b[3m'
            record.underline = '\x1b[4m'
            record.blink = '\x1b[5m'
            record.inverse = '\x1b[7m'

            record.blackFG = '\x1b[30m'
            record.redFG = '\x1b[31m'
            record.greenFG = '\x1b[32m'
            record.yellowFG = '\x1b[33m'
            record.blueFG = '\x1b[34m'
            record.magentaFG = '\x1b[35m'
            record.cyanFG = '\x1b[36m'
            record.whiteFG = '\x1b[37m'

            record.blackBG = '\x1b[30m'
            record.redBG = '\x1b[31m'
            record.greenBG = '\x1b[32m'
            record.yellowBG = '\x1b[33m'
            record.blueBG = '\x1b[34m'
            record.magentaBG = '\x1b[35m'
            record.cyanBG = '\x1b[36m'
            record.whiteBG = '\x1b[37m'

            record.resetTerm = '\x1b[0m'  # normal

        else:
            record.levelColor = ''
            record.bold = ''
            record.underline = ''
            record.blink = ''
            record.inverse = ''
            record.blackFG = ''
            record.redFG = ''
            record.greenFG = ''
            record.yellowFG = ''
            record.blueFG = ''
            record.magentaFG = ''
            record.cyanFG = ''
            record.whiteFG = ''
            record.blackBG = ''
            record.redBG = ''
            record.greenBG = ''
            record.yellowBG = ''
            record.blueBG = ''
            record.magentaBG = ''
            record.cyanBG = ''
            record.whiteBG = ''
            record.resetTerm = ''

        return logging.StreamHandler.emit(self, record)


if __name__ == '__main__':
    import logging.config
    logging.config.dictConfig({
            'version': 1,
            "formatters": {
                "colored": {
                    "format": "%(bold)s%(blackFG)s[%(resetTerm)s%(levelColor)s%(levelname)-8s%(resetTerm)s%(bold)s%(blackFG)s]%(resetTerm)s %(cyanFG)s%(name)s%(bold)s%(blackFG)s:%(resetTerm)s  %(faint)s%(italic)s%(message)s%(resetTerm)s"
                    }
                },
            'handlers': {
                'console': {
                    'class': 'colorlog.ColoredConsoleHandler',
                    'formatter': 'colored',
                    'level': 'DEBUG',
                    'stream': 'ext://sys.stdout'
                    }
                },
            "root": {
                "handlers": [
                    "console",
                    #"file"
                    ],
                "level": 0
                }
            })

    logging.debug("a debug message")
    logging.info("some info")
    logging.warn("a warning")
    logging.error("some error")
    logging.critical("some critical error")

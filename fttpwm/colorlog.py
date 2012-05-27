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

            record.blackForeground = '\x1b[30m'
            record.redForeground = '\x1b[31m'
            record.greenForeground = '\x1b[32m'
            record.yellowForeground = '\x1b[33m'
            record.blueForeground = '\x1b[34m'
            record.magentaForeground = '\x1b[35m'
            record.cyanForeground = '\x1b[36m'
            record.whiteForeground = '\x1b[37m'

            record.blackBackground = '\x1b[30m'
            record.redBackground = '\x1b[31m'
            record.greenBackground = '\x1b[32m'
            record.yellowBackground = '\x1b[33m'
            record.blueBackground = '\x1b[34m'
            record.magentaBackground = '\x1b[35m'
            record.cyanBackground = '\x1b[36m'
            record.whiteBackground = '\x1b[37m'

            record.resetTerm = '\x1b[0m'  # normal

        else:
            record.levelColor = ''
            record.bold = ''
            record.underline = ''
            record.blink = ''
            record.inverse = ''
            record.blackForeground = ''
            record.redForeground = ''
            record.greenForeground = ''
            record.yellowForeground = ''
            record.blueForeground = ''
            record.magentaForeground = ''
            record.cyanForeground = ''
            record.whiteForeground = ''
            record.blackBackground = ''
            record.redBackground = ''
            record.greenBackground = ''
            record.yellowBackground = ''
            record.blueBackground = ''
            record.magentaBackground = ''
            record.cyanBackground = ''
            record.whiteBackground = ''
            record.resetTerm = ''

        return logging.StreamHandler.emit(self, record)


if __name__ == '__main__':
    import logging.config
    logging.config.dictConfig({
            'version': 1,
            "formatters": {
                "colored": {
                    "format": "%(bold)s%(blackForeground)s[%(resetTerm)s%(levelColor)s%(levelname)-8s%(resetTerm)s%(bold)s%(blackForeground)s]%(resetTerm)s %(cyanForeground)s%(name)s%(bold)s%(blackForeground)s:%(resetTerm)s  %(faint)s%(italic)s%(message)s%(resetTerm)s"
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

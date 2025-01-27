import logging

import cairo


logger = logging.getLogger("fttpwm.paint.gradients")


class Direction(object):
    vertical = 0, 0, 0, 1
    horizontal = 0, 0, 1, 0
    diagonalUpLeft = 0, 0, 1, 1
    diagonalUpRight = 0, 1, 1, 0


def linearGradient(orientation, *colors):
    gradient = cairo.LinearGradient(*orientation)

    if len(colors) == 1 and isinstance(colors[0], dict):
        for position, color in sorted(colors[0].iteritems()):
            gradient.add_color_stop_rgba(position, *color)

    else:
        for index, color in enumerate(colors):
            position = float(index) / (len(colors) - 1)
            gradient.add_color_stop_rgba(position, *color)

    return gradient

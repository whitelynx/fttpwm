import cairo


class Direction(object):
    vertical = 0, 0, 0, 1
    horizontal = 0, 0, 1, 0
    diagonalUpLeft = 0, 0, 1, 1
    diagonalUpRight = 0, 1, 1, 0


def addColorStop(gradient, position, color):
    if len(color) == 3:
        gradient.add_color_stop_rgb(position, *color)

    elif len(color) == 4:
        gradient.add_color_stop_rgba(position, *color)


def linearGradient(orientation, *colors):
    gradient = cairo.LinearGradient(*orientation)

    if len(colors) == 1 and isinstance(colors[0], dict):
        for position, color in sorted(colors[0].iteritems()):
            addColorStop(gradient, position, color)

    else:
        for index, color in enumerate(colors):
            position = float(index) / (len(colors) - 1)
            addColorStop(gradient, position, color)

    return gradient

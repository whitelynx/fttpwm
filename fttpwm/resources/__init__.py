from os.path import abspath, dirname, join


def fullPath(resourcePath):
    return join(dirname(abspath(__file__)), 'default-wallpaper.svg')

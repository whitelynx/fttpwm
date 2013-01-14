from os.path import abspath, dirname, join


resourceDir = dirname(abspath(__file__))


def fullPath(resourcePath):
    return join(resourceDir, 'default-wallpaper.svg')

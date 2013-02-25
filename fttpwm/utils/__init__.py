# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: Utility functions

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging


def loggerFor(cls):
    if not isinstance(cls, type):
        cls = type(cls)

    return logging.getLogger('{}.{}'.format(cls.__module__, cls.__name__))


def between(value, lower, upper):
    if lower > upper:
        lower, upper = upper, lower

    return lower < value < upper

# -*- coding: utf-8 -*-
"""FTTPWM: Cairo context helpers

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from contextlib import contextmanager


@contextmanager
def pushContext(context):
    context.save()
    yield
    context.restore()

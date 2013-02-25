# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: Human readability utility functions

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""


def pl(number, singularUnit, pluralUnit=None, noSpace=False):
    """Attach the appropriate singular or plural units to the given number.

    If `pluralUnit` is omitted, it defaults to `singularUnit + "s"`.
    If `noSpace` is True, no space is placed between the number and the unit.

    """
    if pluralUnit is None:
        pluralUnit = singularUnit + "s"

    return '{}{}{}'.format(
            number,
            '' if noSpace else ' ',
            singularUnit if number == 1 else pluralUnit
            )


def listpl(sequence, singularName, pluralName=None, after=False):
    """Attach the appropriate singular or plural units to the given list.

    If `pluralName` is omitted, it defaults to `singularName + "s"`.
    If `after` is True, the name is placed after the list instead of before it.

    """
    if pluralName is None:
        pluralName = singularName + "s"

    try:
        length = len(sequence)
    except TypeError:
        sequence = list(sequence)
        length = len(sequence)

    if after:
        fmt = '{list} {name}'
    else:
        fmt = '{name} {list}'

    return fmt.format(
            name=singularName if length == 1 else pluralName,
            list=naturalJoin(sequence)
            )


def quoteStrings(sequence, quoteChar='"'):
    """Quote a sequence of strings using the given quote character.

    Any backslashes ('\\') will be doubled, and any instances of the quote character will be escaped with backslashes.

    """
    for item in sequence:
        yield '{q}{item}{q}'.format(
                q=quoteChar,
                item=str(item).replace('\\', '\\\\').replace(quoteChar, '\\' + quoteChar)
                )


def naturalJoin(sequence, serialComma=True):
    """Join a list of strings in natural English form.

    If `serialComma` is True (the default), the serial comma is used. (http://en.wikipedia.org/wiki/Serial_comma)

    """
    try:
        length = len(sequence)
    except TypeError:
        sequence = list(sequence)
        length = len(sequence)

    if length == 0:
        return ""
    elif length == 1:
        return sequence[0]
    elif length == 2:
        return "{} and {}".format(*sequence)
    else:
        return "{}{} and {}".format(', '.join(sequence[:-1]), ',' if serialComma else '', sequence[-1])

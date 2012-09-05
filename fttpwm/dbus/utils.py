from __future__ import unicode_literals

import hashlib
from weakref import WeakKeyDictionary


class MemberWrapper(object):
    def __init__(self, memberName, members, **overrides):
        assert len(members) > 0 or len(overrides) > 0
        self.data = WeakKeyDictionary(
                (m.dbus_interface, m) for m in members
                )
        self.data.update(overrides)

        self.__name__ = memberName

    def __getitem__(self, key):
        return self.data.__getitem__(key)

    def __len__(self):
        return self.data.__len__()

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()

    def __iter__(self):
        return self.data.__iter__()

    def iterkeys(self):
        return self.data.iterkeys()

    def itervalues(self):
        return self.data.itervalues()

    def iteritems(self):
        return self.data.iteritems()

    def __get__(self, instance, owner):
        for m in self.values():
            m.dbus_object = instance

        return self

    def __getattr__(self, name):
        if len(self) == 1:
            return getattr(self.values()[0], name)

        else:
            raise TypeError(
                    '{} has {} overloads in different interfaces! You must specify which interface to use; e.g. '
                    '{}[SomeInterface].{}'
                        .format(self.__name__, len(self), self.__name__, name)
                    )


class MethodWrapper(MemberWrapper):
    def __call__(self, *args, **kwargs):
        if len(self) == 1:
            return self.values()[0](*args, **kwargs)
        else:
            raise TypeError(
                    '{} has {} overloads in different interfaces! You must call {}[SomeInterface](...) instead.'
                        .format(self.__name__, len(self), self.__name__)
                    )


class NetDebug(object):
    """This class contains class methods for displaying various network traffic, and for enabling and disabling that
    display.

    """
    # We want background colors in the range [17, 178].
    colorMin = 17
    colorMax = 178
    colorRangeLen = colorMax - colorMin + 1

    enabledTags = dict()

    @classmethod
    def enable(cls, tag):
        cls.enabledTags[tag] = cls._tagColor(tag)

    @classmethod
    def disable(cls, tag):
        del cls.enabledTags[tag]

    @classmethod
    def dataIn(cls, tag, data):
        if tag in cls.enabledTags:
            print("{tagColor} {tag}: \033[1;38;5;16;100m in >>> {data}\033[m".format(
                    tagColor=cls.enabledTags[tag],
                    tag=tag,
                    data=data
                    ))

    @classmethod
    def dataOut(cls, tag, data):
        if tag in cls.enabledTags:
            print("{tagColor} {tag}: \033[1;38;5;16;48;5;236m out <<< {data}\033[m".format(
                    tagColor=cls.enabledTags[tag],
                    tag=tag,
                    data=data
                    ))

    @classmethod
    def _tagColor(cls, tag):
        return '\033[1;38;5;16;48;5;{}m'.format(
                cls.colorMin + sum(map(ord, hashlib.sha1('foo.bar').digest())) % cls.colorRangeLen
                )

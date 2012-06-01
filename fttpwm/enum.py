class _EnumValueMeta(type):
    def __repr__(self):
        return self.__name__


class _EnumValue(object):
    __metaclass__ = _EnumValueMeta


class Enum(type):
    """Use this metaclass to define an enumeration.

    Example:

        >>> class Directions(object):
        ...     __metaclass__ = Enum
        ...     Up = "The up direction."
        ...     Down = "The down direction."
        ...     Left = "The left direction."
        ...     Right = "The right direction."
        ...
        >>> Directions.Up
        Directions.Up
        >>> Directions.Up.__doc__
        'The up direction.'
        >>> Directions.Up == Directions.Up
        True
        >>> Directions.Up == Directions.Down
        False

    """
    def __new__(mcs, name, bases, dict_):
        valueIDs = dict()

        # Create _EnumValue instances for each value in the Enum.
        for attr in dict_.keys():
            if not attr.startswith('_'):
                # Make sure that if two names had the same value in this enum, we keep the replacements the same too.
                if dict_[attr] in valueIDs:
                    dict_[attr] = valueIDs[dict_[attr]]

                    # If this is the preferred name for this value, change the replacement's name to match.
                    if attr in dict_['_preferredNames']:
                        dict_[attr].__name__ = '{}.{}'.format(name, attr)

                else:
                    # We haven't created an _EnumValue for this value yet; create it.
                    class temp(_EnumValue):
                        __doc__ = dict_[attr]

                    temp.__name__ = '{}.{}'.format(name, attr)
                    valueIDs[dict_[attr]] = temp

                    # Replace the original value.
                    dict_[attr] = temp

        # Remove the __metaclass__ attribute so our __doc__ doesn't show up in the resulting Enum's help() output.
        # This may or may not be kosher from a standard Python point of view, but it does make the docs easier to read.
        del dict_['__metaclass__']

        return type.__new__(mcs, name, bases, dict_)

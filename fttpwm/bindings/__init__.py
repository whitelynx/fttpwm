from argparse import Namespace
import logging

from ..settings import settings


logger = logging.getLogger("fttpwm.bindings")


def processBinding(binding):
    if isinstance(binding, (tuple, list)):
        return Namespace(
                onPress=binding[0],
                onRelease=binding[1] if len(binding) > 1 else None,
                onMotion=binding[2] if len(binding) > 2 else None
                )
    elif isinstance(binding, dict):
        return Namespace(**binding)
    elif callable(binding):
        return Namespace(
                onPress=binding,
                onRelease=None,
                onMotion=None
                )
    else:
        return binding


class FilteredHandler(object):
    debugDetailMismatch = False
    debugModifierMismatch = False

    def __init__(self, handler, detail, modifiers=0):
        self.handler = handler
        self.detail = detail
        self.modifiers = modifiers

    def __call__(self, event):
        if event.detail != self.detail:
            if self.debugDetailMismatch:
                logger.debug("FilteredHandler({!r}, {!r}, {!r}): "
                        "event.detail != self.detail ({} != {}); ignoring event!".format(
                            self.handler, self.detail, self.modifiers,
                            *map(bin, (event.detail, self.detail))
                            )
                        )
            return

        if event.state & ~settings.ignoredModifiers != self.modifiers:
            if self.debugModifierMismatch:
                logger.debug("FilteredHandler({!r}, {!r}, {!r}): "
                        "event.state & ~settings.ignoredModifiers != self.modifiers "
                        "({} & ~{} != {}; ~{} = {}; {} & ~{} = {}); ignoring event!".format(
                            self.handler, self.detail, self.modifiers,
                            *map(bin, (event.state, settings.ignoredModifiers, self.modifiers,
                                settings.ignoredModifiers, ~settings.ignoredModifiers,
                                event.state, settings.ignoredModifiers, event.state & ~settings.ignoredModifiers)
                                )
                            )
                        )
            return

        return self.handler(event)

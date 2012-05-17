from argparse import Namespace
import logging


logger = logging.getLogger("fttpwm.bind")


def processBinding(binding):
    if isinstance(binding, (tuple, list)):
        return Namespace(
                onPress=binding[0],
                onRelease=binding[1] if len(binding) > 1 else None,
                onMotion=binding[2] if len(binding) > 2 else None
                )
    elif isinstance(binding, dict):
        return Namespace(**binding)
    else:
        return Namespace(onPress=binding)

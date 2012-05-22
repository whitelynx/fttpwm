from xcb.xproto import Atom

from xpybutil.util import get_atom as atom


# For a KDE-compatible systray, we need to set this property: (to the ID of the root window of this screen?)
atom('_KDE_NET_WM_SYSTEM_TRAY_WINDOW_FOR'), Atom.WINDOW

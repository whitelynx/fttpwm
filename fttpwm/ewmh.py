from xpybutil.util import get_atom as atom


class EWMHAction(object):
    Move = atom('_NET_WM_ACTION_MOVE')
    Resize = atom('_NET_WM_ACTION_RESIZE')
    Minimize = atom('_NET_WM_ACTION_MINIMIZE')
    Shade = atom('_NET_WM_ACTION_SHADE')
    Stick = atom('_NET_WM_ACTION_STICK')
    MaximizeHorz = atom('_NET_WM_ACTION_MAXIMIZE_HORZ')
    MaximizeVert = atom('_NET_WM_ACTION_MAXIMIZE_VERT')
    Fullscreen = atom('_NET_WM_ACTION_FULLSCREEN')
    ChangeDesktop = atom('_NET_WM_ACTION_CHANGE_DESKTOP')
    Close = atom('_NET_WM_ACTION_CLOSE')


class EWMHWindowState(object):
    Modal = atom('_NET_WM_STATE_MODAL')
    Sticky = atom('_NET_WM_STATE_STICKY')
    MaximizedVert = atom('_NET_WM_STATE_MAXIMIZED_VERT')
    MaximizedHorz = atom('_NET_WM_STATE_MAXIMIZED_HORZ')
    Shaded = atom('_NET_WM_STATE_SHADED')
    SkipTaskbar = atom('_NET_WM_STATE_SKIP_TASKBAR')
    SkipPager = atom('_NET_WM_STATE_SKIP_PAGER')
    Hidden = atom('_NET_WM_STATE_HIDDEN')
    Fullscreen = atom('_NET_WM_STATE_FULLSCREEN')
    Above = atom('_NET_WM_STATE_ABOVE')
    Below = atom('_NET_WM_STATE_BELOW')
    DemandsAttention = atom('_NET_WM_STATE_DEMANDS_ATTENTION')


class EWMHWindowType(object):
    Desktop = atom('_NET_WM_WINDOW_TYPE_DESKTOP')
    Dock = atom('_NET_WM_WINDOW_TYPE_DOCK')
    Toolbar = atom('_NET_WM_WINDOW_TYPE_TOOLBAR')
    Menu = atom('_NET_WM_WINDOW_TYPE_MENU')
    Utility = atom('_NET_WM_WINDOW_TYPE_UTILITY')
    Splash = atom('_NET_WM_WINDOW_TYPE_SPLASH')
    Dialog = atom('_NET_WM_WINDOW_TYPE_DIALOG')
    Normal = atom('_NET_WM_WINDOW_TYPE_NORMAL')

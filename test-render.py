import xcb
from xcb.xproto import (Atom, CW, EventMask, PropMode, WindowClass, ButtonPressEvent, ExposeEvent, EnterNotifyEvent,
        LeaveNotifyEvent, KeyPressEvent, GC)
import xcb.render


fontName = "drift"
ops = [(getattr(xcb.render.PictOp, n), n) for n in dir(xcb.render.PictOp) if not n.startswith('_')]
characterInfo = None
white = None
black = None
format = None
titlebars = []


def find_format(screen):
    for d in screen.depths:
        if d.depth == depth:
            for v in d.visuals:
                if v.visual == visual:
                    return v.format

    raise Exception("Failed to find an appropriate Render pictformat!")


def fixedDecimal(intPart, fracPart):
    return intPart << 16 + fracPart


def FIXED(floatValue):
    return int(floatValue * 2 ** 16)


def POINTFIX(x, y):
    return (FIXED(x), FIXED(y))


def COLOR(*args):
    if len(args) == 3:
        args = list(args) + [1]

    assert len(args) == 4

    return [int(x * (2 ** 16 - 1)) for x in args]


def startup():
    global characterInfo, white, black, format

    white = setup.roots[0].white_pixel
    black = setup.roots[0].black_pixel

    cookies = []
    cookies.append(conn.core.CreateWindowChecked(
            depth, window, root,
            0, 0, 640, 480, 0,
            WindowClass.InputOutput,
            visual,
            CW.BackPixel | CW.EventMask,
            [white,
                EventMask.ButtonPress | EventMask.EnterWindow
                    | EventMask.LeaveWindow | EventMask.Exposure | EventMask.KeyPress
                ]
            ))

    cookie = conn.render.QueryPictFormats()
    reply = cookie.reply()
    format = find_format(reply.screens[0])

    name = 'X Python Binding Demo'
    conn.core.ChangeProperty(PropMode.Replace, window, Atom.WM_NAME, Atom.STRING, 8, len(name), name)

    cookies.append(conn.render.CreatePictureChecked(pict, window, format, 0, []))
    cookies.append(conn.render.CreateLinearGradientChecked(
            grad,  # picture
            POINTFIX(0, 0), POINTFIX(616, 440),  # p1, p2
            2, [FIXED(0), FIXED(1)], [COLOR(1, 0, 0, 1), COLOR(0, 1, 0, 0)]  # num_stops, stops, stop_colors
            ))

    cookies.append(conn.core.OpenFontChecked(font, len(fontName), fontName))

    reply = conn.core.QueryFont(font).reply()
    print "Font properties for font {}:".format(fontName)
    for n in dir(reply):
        if not n.startswith('_'):
            print "  {} = {}".format(n, getattr(reply, n))

    maxAscent = 0
    maxDescent = 0
    print "Character properties for font {}:".format(fontName)
    for idx, info in enumerate(reply.char_infos):
        print "  {}: {!r}".format(idx, unichr(idx))
        for n in dir(info):
            if not n.startswith('_'):
                print "    {} = {}".format(n, getattr(info, n))
        maxAscent = max(maxAscent, info.ascent)
        maxDescent = min(maxDescent, info.descent)
    characterInfo = reply.char_infos

    cookies.append(conn.core.CreateGCChecked(fontGC, window,
            GC.Foreground | GC.Background | GC.Font, [black, white, font]))
    cookies.append(conn.core.CloseFontChecked(font))

    cookies.append(conn.render.CreateLinearGradientChecked(
            grad2,  # picture
            POINTFIX(0, 0), POINTFIX(0, maxAscent - maxDescent + 10),  # p1, p2
            2, [FIXED(0), FIXED(1)], [COLOR(1, 0, 0), COLOR(1, 1, 0)]  # num_stops, stops, stop_colors
            ))

    cookies.append(conn.core.MapWindowChecked(window))

    conn.flush()
    for cookie in cookies:
        cookie.check()


def getTextSize(text):
    ascents, descents, widths = zip(*map(
            (lambda x: (x.ascent, x.descent, x.character_width)),
            (characterInfo[ord(char)] for char in text)
            ))

    maxAscent = max(ascents)
    return sum(widths), maxAscent - min(descents), maxAscent


def createTitlebar(title):
    w, h, maxAscent = getTextSize(title)

    cookies = []
    newWin = conn.generate_id()
    newPict = conn.generate_id()
    newGradient = conn.generate_id()
    newFont = conn.generate_id()
    newFontGC = conn.generate_id()

    print w, h
    cookies.append(conn.core.CreateWindowChecked(
            depth, newWin, root,
            0, 0, w, h, 0,
            WindowClass.InputOutput,
            visual,
            CW.BackPixel | CW.EventMask,  # | CW.OverrideRedirect,
            [white,
                EventMask.ButtonPress | EventMask.EnterWindow
                    | EventMask.LeaveWindow | EventMask.Exposure,
                #1
                ]
            ))

    cookies.append(conn.core.ChangePropertyChecked(
            PropMode.Replace, newWin, Atom.WM_NAME, Atom.STRING, 8, len(title), title))

    cookies.append(conn.render.CreatePictureChecked(newPict, newWin, format, 0, []))

    cookies.append(conn.render.CreateLinearGradientChecked(
            newGradient,  # picture
            POINTFIX(0, 0), POINTFIX(0, h + 10),  # p1, p2
            2, [FIXED(0), FIXED(1)], [COLOR(1, 0, 0), COLOR(1, 1, 0)]  # num_stops, stops, stop_colors
            ))

    cookies.append(conn.core.MapWindowChecked(newWin))

    cookies.append(conn.core.OpenFontChecked(newFont, len(fontName), fontName))
    cookies.append(conn.core.CreateGCChecked(newFontGC, newWin,
            GC.Foreground | GC.Background | GC.Font, [black, white, newFont]))
    cookies.append(conn.core.CloseFontChecked(newFont))

    cookies.append(conn.core.ClearAreaChecked(False, newWin, 0, 0, 0, 0))
    cookies.append(conn.core.ImageText8Checked(len(title), newWin, newFontGC, 5, 5 + maxAscent, title))

    cookies.append(conn.render.CompositeChecked(
            xcb.render.PictOp.Multiply,
            newGradient, 0, newPict,  # src,        mask,         dst
            0, 0, 0, 0, 0, 0,         # srcX, srcY, maskX, maskY, dstX, dstY
            w + 10, h + 10            # width, height
            ))

    conn.flush()
    for cookie in cookies:
        print cookie
        cookie.check()

    titlebars.append((title, newWin, newPict, newGradient, newFontGC, w, h, maxAscent))


def paintTitlebar(title, newWin, newPict, newGradient, newFontGC, w, h, maxAscent):
    conn.core.ClearArea(False, newWin, 0, 0, 0, 0)
    conn.core.ImageText8(len(title), newWin, newFontGC, 5, 5 + maxAscent, title)

    conn.render.Composite(
            xcb.render.PictOp.Multiply,
            newGradient, 0, newPict,  # src,        mask,         dst
            0, 0, 0, 0, 0, 0,         # srcX, srcY, maskX, maskY, dstX, dstY
            w + 10, h + 10            # width, height
            )


def paint():
    global ops

    conn.core.ClearArea(False, window, 0, 0, 0, 0)

    curOp = ops[0][0]
    curOpName = ops[0][1]

    msg = "Drawing Operation: {}".format(curOpName)
    print("Drawing text: {!r}".format(msg))
    conn.core.ImageText8(len(msg), window, fontGC, 5, 455, msg)
    w, h, maxAscent = getTextSize(msg)
    conn.render.Composite(
            xcb.render.PictOp.Multiply,
            grad2, 0, pict,                  # src,        mask,         dst
            0, 0, 0, 0, 0, 450 - maxAscent,  # srcX, srcY, maskX, maskY, dstX, dstY
            w + 10, h + 10                   # width, height
            )

    start = 24
    step = 64 + 24
    #for col in xrange(0, 7):
    for x in range(start, 7 * step + start, step):
        #for row in xrange(0, 5):
        for y in range(start, 5 * step + start, step):
            #x = (col + 1) * 24 + col * 64
            #y = (row + 1) * 24 + row * 64
            conn.render.Composite(
                    curOp,
                    grad, 0,    pict,  # src,        mask,         dst
                    x, y, 0, 0, x, y,  # srcX, srcY, maskX, maskY, dstX, dstY
                    64, 64             # width, height
                    )

    for titlebar in titlebars:
        paintTitlebar(*titlebar)

    conn.flush()


def paintChecked():
    global ops

    cookies = []
    cookies.append(conn.core.ClearAreaChecked(False, window, 0, 0, 0, 0))

    msg = "Drawing Operation: {}".format(ops[0][1])
    print("Drawing text: {!r}".format(msg))
    cookies.append(conn.core.ImageText8Checked(len(msg), window, fontGC, 5, 455, msg))
    w, h, maxAscent = getTextSize(msg)
    cookies.append(conn.render.CompositeChecked(
            xcb.render.PictOp.Multiply,
            grad2, 0, pict,                # src,        mask,         dst
            0, 0, 0, 0, 0, 450 - maxAscent,  # srcX, srcY, maskX, maskY, dstX, dstY
            w + 1000, h + 1000                   # width, height
            ))

    for col in xrange(0, 7):
        for row in xrange(0, 5):
            x = (col + 1) * 24 + col * 64
            y = (row + 1) * 24 + row * 64
            cookies.append(conn.render.CompositeChecked(
                    ops[0][0],
                    grad, 0,    pict,  # src,        mask,         dst
                    x, y, 0, 0, x, y,  # srcX, srcY, maskX, maskY, dstX, dstY
                    64, 64             # width, height
                    ))

    conn.flush()
    for cookie in cookies:
        cookie.check()


def nextOp():
    global ops
    ops.append(ops.pop(0))
    print "Switched to next PictOp:", ops[0][1]
    paint()


def prevOp():
    global ops
    ops.insert(0, ops.pop())
    print "Switched to previous PictOp:", ops[0][1]
    paint()


def run():
    startup()
    print 'Click in window to exit.'

    while True:
        try:
            event = conn.wait_for_event()

        except xcb.ProtocolException, error:
            print "Protocol error %s received!" % error.__class__.__name__
            break

        except:
            print "Unexpected error received: %s" % error.message
            break

        if isinstance(event, ExposeEvent):
            paint()

        elif isinstance(event, EnterNotifyEvent):
            print 'Enter (%d, %d)' % (event.event_x, event.event_y)

        elif isinstance(event, LeaveNotifyEvent):
            print 'Leave (%d, %d)' % (event.event_x, event.event_y)

        elif isinstance(event, ButtonPressEvent):
            print 'Button %d down' % event.detail
            break

        elif isinstance(event, KeyPressEvent):
            print 'Key %s down; state: %r' % (event.detail, event.state)
            if event.detail == 39:
                if event.state & xcb.xproto.ModMask.Shift == xcb.xproto.ModMask.Shift:
                    prevOp()
                else:
                    nextOp()
            elif event.detail == 53:
                print '"Q" pressed; exiting.'
                break
            elif event.detail == 45:
                createTitlebar("(A new window! Imagine that!)0Oo.")

        else:
            print 'Got event:', event, dir(event)

    conn.disconnect()


conn = xcb.connect()
conn.render = conn(xcb.render.key)
print '\n  '.join(['conn:'] + dir(conn))
print '\n  '.join(['conn.render:'] + dir(conn.render))

setup = conn.get_setup()
root = setup.roots[0].root
depth = setup.roots[0].root_depth
visual = setup.roots[0].root_visual

window = conn.generate_id()
pict = conn.generate_id()
grad = conn.generate_id()
grad2 = conn.generate_id()
font = conn.generate_id()
fontGC = conn.generate_id()

run()

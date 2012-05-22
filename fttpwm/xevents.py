import array
import collections
import struct

import xcb.xproto


_event_ids = dict(
        (cls.__name__, eid)
        for eid, cls in xcb.xproto._events.iteritems()
        )


class _EvFact(struct.Struct):
    def __init__(self, name, fmt, fieldNames):
        self.event_id = _event_ids[name]

        # Add the 'event_id' field, which is common to all events.
        fmt = '=B' + fmt
        fieldNames = 'event_id, ' + fieldNames

        self.ResultType = collections.namedtuple(name, fieldNames)

        super(_EvFact, self).__init__(fmt)

        # X events cannot be more than 32 bytes in length. If we are, we were incorrectly constructed.
        assert self.size <= 32

        # Add a docstring to build so it's easier to discover what you should pass.
        # (we can't just assign to self.build.__doc__ because it's an instancemethod)
        def build(*args, **kwargs):
            return self.__build(*args, **kwargs)

        build.__doc__ = '''
                Build a %s object.

                Parameters:
                    %s
                ''' % (name, fieldNames)
        self.build = build

    def __call__(self, data, offset=0):
        return self.ResultType(*self.unpack_from(data, offset))

    def __build(self, *args, **kwargs):
        # Make sure we don't pass event_id twice. (remove it from kwargs if it exists)
        if kwargs.pop('event_id', self.event_id) != self.event_id:
            # If the user actually did specify event_id and it doesn't match ours, something is _seriously_ wrong.
            raise ValueError("Invalid event_id specified! Must be %s." % (self.event_id, ))

        return self.pack(*self.ResultType(self.event_id, *args, **kwargs))


KeyPressEvent = _EvFact('KeyPressEvent', 'B2xIIIIhhhhHBx',
        'detail, time, root, event, child, root_x, root_y, event_x, event_y, state, same_screen')

KeyReleaseEvent = _EvFact('KeyReleaseEvent', 'B2xIIIIhhhhHBx',
        'detail, time, root, event, child, root_x, root_y, event_x, event_y, state, same_screen')

ButtonPressEvent = _EvFact('ButtonPressEvent', 'B2xIIIIhhhhHBx',
        'detail, time, root, event, child, root_x, root_y, event_x, event_y, state, same_screen')

ButtonReleaseEvent = _EvFact('ButtonReleaseEvent', 'B2xIIIIhhhhHBx',
        'detail, time, root, event, child, root_x, root_y, event_x, event_y, state, same_screen')

MotionNotifyEvent = _EvFact('MotionNotifyEvent', 'B2xIIIIhhhhHBx',
        'detail, time, root, event, child, root_x, root_y, event_x, event_y, state, same_screen')

EnterNotifyEvent = _EvFact('EnterNotifyEvent', 'B2xIIIIhhhhHBB',
        'detail, time, root, event, child, root_x, root_y, event_x, event_y, state, mode, same_screen_focus')

LeaveNotifyEvent = _EvFact('LeaveNotifyEvent', 'B2xIIIIhhhhHBB',
        'detail, time, root, event, child, root_x, root_y, event_x, event_y, state, mode, same_screen_focus')

FocusInEvent = _EvFact('FocusInEvent', 'B2xIB3x',
        'detail, event, mode')

FocusOutEvent = _EvFact('FocusOutEvent', 'B2xIB3x',
        'detail, event, mode')

#FIXME! This will require using the 'array' module.
#KeymapNotifyEvent = _EvFact('KeymapNotifyEvent', 'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB',
#        'response_type, keys[31]')

ExposeEvent = _EvFact('ExposeEvent', 'x2xIHHHHH2x',
        'window, x, y, width, height, count')

GraphicsExposureEvent = _EvFact('GraphicsExposureEvent', 'x2xIHHHHHHB3x',
        'drawable, x, y, width, height, minor_opcode, count, major_opcode')

NoExposureEvent = _EvFact('NoExposureEvent', 'x2xIHBx',
        'drawable, minor_opcode, major_opcode')

VisibilityNotifyEvent = _EvFact('VisibilityNotifyEvent', 'x2xIB3x',
        'window, state')

CreateNotifyEvent = _EvFact('CreateNotifyEvent', 'x2xIIhhHHHBx',
        'parent, window, x, y, width, height, border_width, override_redirect')

DestroyNotifyEvent = _EvFact('DestroyNotifyEvent', 'x2xII',
        'event, window')

UnmapNotifyEvent = _EvFact('UnmapNotifyEvent', 'x2xIIB3x',
        'event, window, from_configure')

MapNotifyEvent = _EvFact('MapNotifyEvent', 'x2xIIB3x',
        'event, window, override_redirect')

MapRequestEvent = _EvFact('MapRequestEvent', 'x2xII',
        'parent, window')

ReparentNotifyEvent = _EvFact('ReparentNotifyEvent', 'x2xIIIhhB3x',
        'event, window, parent, x, y, override_redirect')

ConfigureNotifyEvent = _EvFact('ConfigureNotifyEvent', 'x2xIIIhhHHHBx',
        'event, window, above_sibling, x, y, width, height, border_width, override_redirect')

ConfigureRequestEvent = _EvFact('ConfigureRequestEvent', 'B2xIIIhhHHHH',
        'stack_mode, parent, window, sibling, x, y, width, height, border_width, value_mask')

GravityNotifyEvent = _EvFact('GravityNotifyEvent', 'x2xIIhh',
        'event, window, x, y')

ResizeRequestEvent = _EvFact('ResizeRequestEvent', 'x2xIHH',
        'window, width, height')

CirculateNotifyEvent = _EvFact('CirculateNotifyEvent', 'x2xII4xB3x',
        'event, window, place')

CirculateRequestEvent = _EvFact('CirculateRequestEvent', 'x2xII4xB3x',
        'event, window, place')

PropertyNotifyEvent = _EvFact('PropertyNotifyEvent', 'x2xIIIB3x',
        'window, atom, time, state')

SelectionClearEvent = _EvFact('SelectionClearEvent', 'x2xIII',
        'time, owner, selection')

SelectionRequestEvent = _EvFact('SelectionRequestEvent', 'x2xIIIIII',
        'time, owner, requestor, selection, target, property')

SelectionNotifyEvent = _EvFact('SelectionNotifyEvent', 'x2xIIIII',
        'time, requestor, selection, target, property')

ColormapNotifyEvent = _EvFact('ColormapNotifyEvent', 'x2xIIBB2x',
        'window, colormap, new, state')

#FIXME! This will require using the 'array' module, and figuring out how we want to do unions.
#ClientMessageEvent = _EvFact('ClientMessageEvent', 'B2xIIBBBBBBBBBBBBBBBBBBBB|xB2xIIHHHHHHHHHH|xB2xIIIIIII',
#        'format, window, message_type, data[20] | data[10] | data[5]')

MappingNotifyEvent = _EvFact('MappingNotifyEvent', 'x2xBBBx',
        'request, first_keycode, count')


# Some notes on the structure of ClientMessageEvent:
#   xpyb uses:     'xB2xII'  => 'xBxxI___I___' + ['I___' * 5 | 'H_' * 10 | 'B' * 20] (items)
#       with the arguments: format, window, message_type, (*items)
#   xpybutil uses: 'BBH7I'   => 'BBH_I___I___' +  'I___' * 5 (items)
#       with the arguments: Event.ClientMessageEvent, format=32, sequence=0, window, message_type, (*items)
#   xpyb ignores the event type (leftmost byte) because it's only reading, not writing.
#
#   ClientMessageEvent contains a ClientMessageData (union of 20 * [CARD8], 10 * [CARD16], 5 * [CARD32]) at offset=12;
#   append array('B', items), array('H', items), or array('I', items) respectively to add items to the event. (make
#   sure to pad the array to the correct length with zeros!)

# Copyright (c) 2023 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import xcffib.xinput
import xcffib.xproto
import xcffib.xtest

from test.conftest import dualmonitor


@dualmonitor
def test_pointer(xmanager):
    """Two screens should result in 1 pointer barrier."""
    _, barriers = xmanager.c.eval("len(self.core.conn.xfixes.barriers.keys())")
    assert int(barriers) == 1


def test_no_pointer(xmanager):
    """One screen should result in 0 pointer barriers."""
    _, barriers = xmanager.c.eval("len(self.core.conn.xfixes.barriers.keys())")
    assert int(barriers) == 0


@dualmonitor
def test_screen_focus(xmanager, conn):
    def current_screen():
        _, index = xmanager.c.eval("self.current_screen.index")
        return int(index)

    assert current_screen() == 0

    _, barrier_key = xmanager.c.eval("list(self.core.conn.xfixes.barriers.keys())[0]")  # There's only one barrier in this configuration
    barrier = int(barrier_key)

    # Code from actual event
    # 2023-11-05 14:15:29,102 WARNING libqtile core.py:handle_BarrierHit():L816
    # {'unpacker': <xcffib.CffiUnpacker object at 0x7fba2f0fe190>, 'response_type': 35, 'sequence': 2126, 'extension': 131,
    # 'length': 9, 'event_type': 25, 'full_sequence': 2126, 'deviceid': 2, 'time': 4159579, 'eventid': 1, 'root': 1944,
    # 'event': 1944, 'barrier': 4194628, 'dtime': 0, 'flags': 0, 'sourceid': 11, 'root_x': 54132736, 'root_y': 19660800, 
    # 'dx': <xcffib.xinput.FP3232 object at 0x7fba2f0fea90>, 'dy': <xcffib.xinput.FP3232 object at 0x7fba2f0fe0d0>, 'bufsize': 62}

    # BarrierHitEvent.synthetic(deviceid, time, eventid, root, event, barrier, dtime, flags, sourceid, root_x, root_y, dx, dy)

    assert current_screen() == 0

    event = xcffib.xinput.BarrierHitEvent.synthetic(
        2,
        xcffib.xproto.Time.CurrentTime,
        1,
        conn.default_screen.root.wid,
        conn.default_screen.root.wid,
        barrier,
        0,
        0,
        11,
        799 << 16,
        100 << 16,
        (0, 0),
        (0, 0)
    )

    conn.conn.core.SendEvent(False, conn.default_screen.root.wid, xcffib.xproto.EventMask.NoEvent, event.pack())
    conn.conn.flush()
    conn.xsync()

    # Second screen should now be focused
    assert current_screen() == 1

    event = xcffib.xinput.BarrierHitEvent.synthetic(
        2,
        xcffib.xproto.Time.CurrentTime,
        1,
        conn.default_screen.root.wid,
        conn.default_screen.root.wid,
        barrier,
        0,
        0,
        11,
        800 << 16,
        100 << 16,
        (0, 0),
        (0, 0)
    )

    conn.conn.core.SendEvent(False, conn.default_screen.root.wid, xcffib.xproto.EventMask.NoEvent, event.pack())
    conn.conn.flush()
    conn.xsync()

    # Second screen should now be focused
    assert current_screen() == 0

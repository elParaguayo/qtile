import pytest

import libqtile.bar
import libqtile.config
import libqtile.widget
from test.conftest import BareConfig


class HoverCounter(libqtile.widget.TextBox):
    """TextBox that counts mouse_enter / mouse_leave calls."""

    def __init__(self, **kwargs):
        libqtile.widget.TextBox.__init__(self, **kwargs)
        self.enter_count = 0
        self.leave_count = 0

    def mouse_enter(self, x, y):
        self.enter_count += 1

    def mouse_leave(self, x, y):
        self.leave_count += 1


class HoverConfig(BareConfig):
    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [HoverCounter(text="hov", name="hov")],
                30,
            ),
        ),
    ]


hover_config = pytest.mark.parametrize("wmanager", [HoverConfig], indirect=True)


@hover_config
def test_bar_widget_pointer_events(wmanager):
    """Cursor crossing a bar widget fires mouse_enter / mouse_leave."""
    enter = 'self.widgets_map["hov"].enter_count'
    leave = 'self.widgets_map["hov"].leave_count'

    # Cursor outside the bar — no events.
    wmanager.backend.fake_motion(400, 400)
    wmanager.c.sync()
    assert int(wmanager.c.eval(enter)) == 0
    assert int(wmanager.c.eval(leave)) == 0

    # Move into the top bar over the widget.
    wmanager.backend.fake_motion(10, 10)
    wmanager.c.sync()
    assert int(wmanager.c.eval(enter)) == 1
    assert int(wmanager.c.eval(leave)) == 0

    # Move back out.
    wmanager.backend.fake_motion(400, 400)
    wmanager.c.sync()
    assert int(wmanager.c.eval(enter)) == 1
    assert int(wmanager.c.eval(leave)) == 1

    # Re-entering increments enter_count again.
    wmanager.backend.fake_motion(10, 10)
    wmanager.c.sync()
    assert int(wmanager.c.eval(enter)) == 2
    assert int(wmanager.c.eval(leave)) == 1

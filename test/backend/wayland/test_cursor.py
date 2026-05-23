from pathlib import Path

import pytest

from test.helpers import Retry

pytest.importorskip("libqtile.backend.wayland.core")

CLIENT = Path(__file__) / ".." / ".." / ".." / "wayland_clients" / "bin" / "cursor-shape-v1"


@pytest.mark.parametrize("shape", ["crosshair", "text", "wait", "help"])
def test_cursor_shape_protocol(wmanager, shape):
    """Test that the C client can successfully request shapes via the protocol."""

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_window():
        assert len(wmanager.c.windows()) > 0

    def cursor_name():
        return wmanager.c.core.get_cursor_shape_v1()

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_cursor():
        assert cursor_name() != "default"

    wmanager.c.spawn(f"{CLIENT.resolve().as_posix()} -c {shape}")
    print(f"{CLIENT.resolve().as_posix()}")

    wait_for_window()
    wmanager.c.window.set_position_floating(100, 100)
    print(wmanager.c.window.info())
    wmanager.c.eval("self.core.warp_pointer(0, 0, motion=True)")
    assert cursor_name() == "default"

    wmanager.c.eval("self.core.warp_pointer(110, 110, motion=True)")
    wait_for_cursor()
    wmanager.c.spawn(f"grim -c /tmp/cursor-{shape}.png")
    cursor = cursor_name()

    if shape == "wait":
        assert cursor in ["wait", "watch"]
    elif shape == "help":
        assert cursor in ["help", "whats_this", "question_arrow"]
    else:
        assert cursor == shape

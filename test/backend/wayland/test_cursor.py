from pathlib import Path

import pytest

from test.helpers import Retry

pytest.importorskip("libqtile.backend.wayland.core")

CLIENT_PATH = Path(__file__) / ".." / ".." / ".." / "wayland_clients" / "bin"
POINTER = CLIENT_PATH / "virtual-pointer"
CURSOR_CLIENT = CLIENT_PATH / "cursor-shape-v1"


@pytest.fixture
def vpmanager(wmanager):
    """Starts a virtual pointer client before yielding the manager."""
    # pid = wmanager.c.spawn(f"{POINTER.resolve().as_posix()}")
    # if pid < 1:
    #     assert False, "Couldn't start pointer"
    # try:
    yield wmanager
    # finally:
    #     if pid > 1:
    #         os.kill(pid, signal.SIGTERM)


@pytest.mark.parametrize("shape", ["crosshair", "text", "wait", "help"])
def test_cursor_shape_protocol(vpmanager, shape):
    """Test that the C client can successfully request shapes via the protocol."""

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_window():
        assert len(vpmanager.c.windows()) > 0

    def cursor_name():
        return vpmanager.c.core.get_cursor_shape_v1()

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_cursor():
        assert cursor_name() != "default"

    vpmanager.c.spawn(f"{CURSOR_CLIENT.resolve().as_posix()} -c {shape}")

    wait_for_window()
    vpmanager.c.window.set_position_floating(100, 100)
    print(vpmanager.c.window.info())
    vpmanager.c.eval("self.core.warp_pointer(0, 0, motion=True)")
    assert cursor_name() == "default"

    vpmanager.c.eval("self.core.warp_pointer(110, 110)")
    vpmanager.c.eval("self.core.warp_pointer(115, 115)")
    _ = vpmanager.c.core.stacking_info()
    # vpmanager.c.spawn(f"grim -c /tmp/cursor-{shape}.png")
    wait_for_cursor()
    cursor = cursor_name()

    if shape == "wait":
        assert cursor in ["wait", "watch"]
    elif shape == "help":
        assert cursor in ["help", "whats_this", "question_arrow"]
    else:
        assert cursor == shape

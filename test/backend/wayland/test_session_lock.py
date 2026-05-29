import os
import subprocess
from pathlib import Path
from types import MethodType

import pytest

from libqtile.backend.wayland._ffi import lib
from libqtile.command.base import CommandError
from test.conftest import dualmonitor

CLIENT = (
    (Path(__file__).parent / ".." / ".." / "wayland_clients" / "bin" / "session-lock-v1")
    .resolve()
    .as_posix()
)


class LockState:
    LOCKED = lib.QW_SESSION_LOCK_LOCKED
    UNLOCKED = lib.QW_SESSION_LOCK_UNLOCKED
    CRASHED = lib.QW_SESSION_LOCK_CRASHED


class ScriptError(Exception):
    pass


class SesionLockClient:
    def __init__(self, manager):
        self.process = None
        self.manager = manager

    def __enter__(self):
        self.process = subprocess.Popen(
            [CLIENT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=make_test_env(self.manager),
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.process and self.process.poll() is None:
                self.process.stdin.write("quit\n")
                self.process.stdin.flush()

                self.process.wait(timeout=2)

        except subprocess.TimeoutExpired:
            self.process.kill()

        finally:
            if self.process:
                self.process.stdin.close()
                self.process.stdout.close()
                self.process.stderr.close()

    def flush_manager(self):
        self.manager.c.core.flush()

    def send(self, command: str) -> str:
        """
        Send a command and wait for one-line response.

        Expected responses:
            OK
            ERROR: message
        """
        if self.process is None:
            raise ScriptError("Process not started")

        if self.process.poll() is not None:
            raise ScriptError("Process has exited")
        self.flush_manager()
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()
        self.flush_manager()
        response = self.process.stdout.readline()

        if response == "":
            stderr = self.process.stderr.read().strip()
            raise ScriptError(f"Process closed stdout. stderr={stderr}")

        return response.strip()

    def assert_ok(self, command: str) -> None:
        assert self.send(command) == "OK"

    def assert_error(self, command: str, error: str) -> None:
        assert self.send(command) == f"ERROR: {error}"


@pytest.fixture
def ipc_enable(request):
    """Convenience fixture to enable IPC when locked."""
    yield getattr(request, "param", False)


enable_ipc = pytest.mark.parametrize("ipc_enable", [True], indirect=True)


def find_layer_lock(stacking_info):
    """Recursively search the nested stacking tree for the LAYER_LOCK node."""
    if not isinstance(stacking_info, dict):
        return None

    # Check current node
    if stacking_info.get("name") == "LAYER_LOCK":
        return stacking_info

    # Recurse through children
    for child in stacking_info.get("children", []):
        result = find_layer_lock(child)
        if result is not None:
            return result

    return None


def find_node_at_position(node, node_type, x, y, parent_x=0, parent_y=0):
    """
    Looks for a node at given position but, as tree nodes are relative,
    we need to track absolute position of child node.
    """
    if not isinstance(node, dict):
        return False

    abs_x = parent_x + node["x"]
    abs_y = parent_y + node["y"]

    if node["type"] == node_type:
        return abs_x == x and abs_y == y

    for child in node.get("children", []):
        result = find_node_at_position(
            child,
            node_type,
            x,
            y,
            abs_x,
            abs_y,
        )
        if result:
            return True

    return False


def count_node_types(node, counts=None):
    if counts is None:
        counts = {}

    if not isinstance(node, dict):
        return counts

    # Count current node type
    node_type = node.get("type")
    if node_type:
        counts[node_type] = counts.get(node_type, 0) + 1

    # Recurse through children
    for child in node.get("children", []):
        count_node_types(child, counts)

    return counts


@pytest.fixture
def lock_manager(wmanager, ipc_enable):
    """Modified manager instance with additional methods to test session lock."""

    def remove_hooks(self) -> None:
        self.c.eval("del hook.subscriptions['qtile']['locked']")
        self.c.eval("del hook.subscriptions['qtile']['unlocked']")

    def _lock_state(self) -> int:
        return int(self.c.core.eval("self.qw.lock_state"))

    def assert_locked(self) -> None:
        assert self._lock_state() == LockState.LOCKED

    def assert_unlocked(self) -> None:
        assert self._lock_state() == LockState.UNLOCKED

    def assert_crashed(self) -> None:
        assert self._lock_state() == LockState.CRASHED

    def _get_layer_lock(self) -> dict:
        info = self.c.core.stacking_info()
        layer = find_layer_lock(info)
        assert layer
        return layer

    def assert_layer_lock_enabled(self, enabled):
        assert self._get_layer_lock()["enabled"] == enabled

    def assert_rect_at_position(self, x, y):
        layer = self._get_layer_lock()
        assert find_node_at_position(layer, "rect", x, y)

    def assert_buffer_at_position(self, x, y):
        layer = self._get_layer_lock()
        assert find_node_at_position(layer, "buffer", x, y)

    def assert_rect_count(self, num):
        layer = self._get_layer_lock()
        counts = count_node_types(layer)
        assert counts.get("rect", 0) == num

    def assert_buffer_count(self, num):
        layer = self._get_layer_lock()
        counts = count_node_types(layer)
        assert counts.get("buffer", 0) == num

    # bind methods to our manager instance
    for f in [
        remove_hooks,
        _lock_state,
        assert_locked,
        assert_unlocked,
        assert_crashed,
        _get_layer_lock,
        assert_layer_lock_enabled,
        assert_rect_at_position,
        assert_buffer_at_position,
        assert_rect_count,
        assert_buffer_count,
    ]:
        setattr(wmanager, f.__name__, MethodType(f, wmanager))

    # When the session is locked, IPC is disabled by default.
    # However, for testing, we need access to the internals so we
    # re-enable IPC by removing the hooks in the server.
    if ipc_enable:
        wmanager.remove_hooks()

    yield wmanager


def make_test_env(mgr):
    """Generate environment variables to ensure client connects to test server."""
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(mgr.backend.env)
    return env


@enable_ipc
def test_session_lock_server(lock_manager):
    """Basic test of locked state."""
    with SesionLockClient(lock_manager) as client:
        # Session is unlocked so layer lock is disabled
        lock_manager.assert_layer_lock_enabled(False)

        # Lock then client and verify lock state and layer_lock state
        client.assert_ok("lock")
        lock_manager.assert_locked()
        lock_manager.assert_layer_lock_enabled(True)

        # Check state is reset after unlock
        client.assert_ok("unlock")
        lock_manager.assert_unlocked()
        lock_manager.assert_layer_lock_enabled(False)


def test_session_lock_client(lock_manager):
    """Check that correct messages are sent to clients."""
    with SesionLockClient(lock_manager) as client:
        client.assert_ok("lock")
        client.assert_ok("check_locked")

        client.assert_ok("unlock")
        client.assert_ok("check_unlocked")


def test_ipc_disabled(lock_manager):
    """
    Confirm IPC is unavailable when locked and re-enabled when lock is removed.
    """
    with SesionLockClient(lock_manager) as client:
        client.assert_ok("lock")
        with pytest.raises(CommandError):
            lock_manager.assert_locked()

        # Unlocking should re-enable IPC
        client.assert_ok("unlock")
        lock_manager.assert_unlocked()


@enable_ipc
def test_crashed(lock_manager):
    """Confirm crashed state is still locked."""
    with SesionLockClient(lock_manager) as client:
        client.assert_ok("lock")
        lock_manager.assert_layer_lock_enabled(True)

        client.assert_ok("quit")
        lock_manager.assert_crashed()
        lock_manager.assert_layer_lock_enabled(True)

    with SesionLockClient(lock_manager) as new_client:
        new_client.assert_error("lock", "compositor rejected lock")
        new_client.assert_error("unlock", "no active lock")


def test_crashed_ipc_disabled(lock_manager):
    """Confirm IPC is still locked when in crashed state."""
    with SesionLockClient(lock_manager) as client:
        client.assert_ok("lock")
        client.assert_ok("quit")
        with pytest.raises(CommandError):
            lock_manager.assert_crashed()


@enable_ipc
def test_multiple_lock_requests(lock_manager):
    """Multiple requests for a lock should be rejected."""
    with SesionLockClient(lock_manager) as client:
        client.assert_ok("lock")
        lock_manager.assert_locked()

        client.assert_error("lock", "compositor rejected lock")
        lock_manager.assert_locked()

        client.assert_ok("unlock")
        lock_manager.assert_unlocked()


@enable_ipc
def test_lock_surface_single(lock_manager):
    """Check that lock surface is added to LAYER_LOCK."""
    with SesionLockClient(lock_manager) as client:
        lock_manager.assert_rect_count(1)
        lock_manager.assert_rect_at_position(0, 0)

        lock_manager.assert_buffer_count(0)

        client.assert_ok("lock")
        client.assert_ok("create_surface")
        client.assert_ok("check_surface_count 1")

        lock_manager.assert_buffer_count(1)
        lock_manager.assert_buffer_at_position(0, 0)

        client.assert_ok("unlock")
        lock_manager.assert_buffer_count(0)


@dualmonitor
@enable_ipc
def test_lock_surface_dualmonito(lock_manager):
    """
    Check that lock surfaces are added to LAYER_LOCK and
    positioned correctly on multiple monitors.
    """
    with SesionLockClient(lock_manager) as client:
        lock_manager.assert_rect_count(2)
        lock_manager.assert_rect_at_position(0, 0)
        lock_manager.assert_rect_at_position(800, 0)

        lock_manager.assert_buffer_count(0)

        client.assert_ok("lock")
        client.assert_ok("create_surface")
        client.assert_ok("check_surface_count 2")

        lock_manager.assert_buffer_count(2)
        lock_manager.assert_buffer_at_position(0, 0)
        lock_manager.assert_buffer_at_position(800, 0)

        client.assert_ok("unlock")
        lock_manager.assert_buffer_count(0)

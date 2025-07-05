# Copyright (c) 2022 elParaguayo
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
import sys
from types import ModuleType

import pytest

from libqtile import widget
from libqtile.bar import Bar
from libqtile.config import Screen
from test.helpers import BareConfig


class MockXDG(ModuleType):
    def getIconPath(*args, **kwargs):  # noqa: N802
        pass


@pytest.fixture
def position(request):
    return getattr(request, "param", "top")


horizontal_and_vertical = pytest.mark.parametrize("position", ["top", "left"], indirect=True)


@pytest.fixture
def launchbar_manager(request, manager_nospawn, position):
    config = getattr(request, "param", dict())

    class LaunchBarConfig(BareConfig):
        screens = [
            Screen(
                **{position: Bar([widget.LaunchBar(progs=[("test", "test", "")], **config)], 28)}
            )
        ]

    manager_nospawn.start(LaunchBarConfig)
    yield manager_nospawn


def test_deprecated_configuration(caplog, monkeypatch):
    monkeypatch.setitem(sys.modules, "xdg.IconTheme", MockXDG("xdg.IconTheme"))
    _ = widget.LaunchBar(
        [("thunderbird", "thunderbird -safe-mode", "launch thunderbird in safe mode")]
    )
    records = [r for r in caplog.records if r.msg.startswith("The use of")]
    assert records
    assert "The use of a positional argument in LaunchBar is deprecated." in records[0].msg


@horizontal_and_vertical
def test_tasklist_defaults(launchbar_manager):
    widget = launchbar_manager.c.widget["launchbar"]
    assert widget.info()["length"] > 0

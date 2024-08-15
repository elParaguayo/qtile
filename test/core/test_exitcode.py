# Copyright (c) 2024 Thomas Krug
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

import os
import subprocess
import sys
import threading
import time

import pytest

import libqtile

repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, repo_path)


class MinimalConfig(libqtile.confreader.Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
    ]
    layouts = [libqtile.layout.MonadTall()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


minimal_config = pytest.mark.parametrize("manager", [MinimalConfig], indirect=True)


# TODO this probably ignores the requested backend by pytest (and always uses X11)
def run_qtile():
    cmd = "bin/qtile"
    cmd = os.path.join(repo_path, cmd)
    args = [cmd, "start"]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    out, err = proc.communicate(timeout=10)
    exitcode = proc.returncode
    return exitcode


def stop_qtile(code):
    cmd = "bin/qtile"
    cmd = os.path.join(repo_path, cmd)
    args = [cmd, "cmd-obj", "-o", "cmd", "-f", "shutdown"]
    if code:
        args.extend(["-a", str(code)])
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    out, err = proc.communicate(timeout=10)
    exitcode = proc.returncode
    return exitcode


def deferred_stop(code=0):
    # wait for qtile process to start
    time.sleep(3)
    stop_qtile(code)


@minimal_config
def test_exitcode_default(manager):
    thread = threading.Thread(target=deferred_stop)
    thread.start()

    exitcode = run_qtile()

    assert exitcode == 0


@minimal_config
def test_exitcode_explicit(manager):
    code = 23

    thread = threading.Thread(target=deferred_stop, args=(code,))
    thread.start()

    exitcode = run_qtile()

    assert exitcode == code

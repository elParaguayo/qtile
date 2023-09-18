# Copyright (c) 2023, elParaguayo
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
from pathlib import Path

import setuptools.build_meta as sbm
from setuptools.build_meta import LEGACY_EDITABLE

ROOT = Path(__file__).parent.resolve()


def run_ffibuild():
    """
    Calls the FFI build script and ensures the folder is in the
    python path.
    """
    print("Running ffibuild...")
    sys.path.insert(0, ROOT.as_posix())
    python_path = ":".join(sys.path)
    try:
        subprocess.run(
            [sys.executable, "scripts/ffibuild"],
            check=True,
            env=os.environ | {"PYTHONPATH": python_path},
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        print("Error when running ffibuild:")
        print(e.stdout)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Tries to build the wayland CFFI bindings before building the wheel."""
    run_ffibuild()

    # Then do the setuptools build
    return sbm.build_wheel(
        wheel_directory,
        config_settings=config_settings,
        metadata_directory=metadata_directory,
    )


# Preserve all other entry points from setuptools.build_meta
get_requires_for_build_wheel = sbm.get_requires_for_build_wheel
get_requires_for_build_sdist = sbm.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = sbm.prepare_metadata_for_build_wheel
build_sdist = sbm.build_sdist

# Use same test as per setuptools.build_meta
if not LEGACY_EDITABLE:
    get_requires_for_build_editable = sbm.get_requires_for_build_editable
    prepare_metadata_for_build_editable = sbm.prepare_metadata_for_build_editable
    build_editable = sbm.build_editable

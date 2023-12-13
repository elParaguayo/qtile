# Copyright (c) 2015 dmpayton
# Copyright (c) 2021 elParaguayo
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
import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock

from docs.qtile_docs.templates import qtile_class_template
from libqtile import command, configurable, widget
from libqtile.utils import import_class


def sphinx_escape(txt):
    return txt


def qtile_class(classname, no_config=False, no_commands=False):
    module, class_name = classname.rsplit(".", 1)
    obj = import_class(module, class_name)
    is_configurable = not no_config
    is_commandable = not no_commands
    is_widget = issubclass(obj, widget.base._Widget)

    # build up a dict of defaults using reverse MRO
    defaults = {}
    for klass in reversed(obj.mro()):
        if not issubclass(klass, configurable.Configurable):
            continue
        if not hasattr(klass, "defaults"):
            continue
        klass_defaults = getattr(klass, "defaults")
        defaults.update({d[0]: d[1:] for d in klass_defaults})
    # turn the dict into a list of ("value", "default", "description") tuples
    defaults = [
        (k, sphinx_escape(v[0]), sphinx_escape(v[1])) for k, v in sorted(defaults.items())
    ]
    if len(defaults) == 0:
        is_configurable = False

    is_widget = issubclass(obj, widget.base._Widget)

    if is_widget:
        index = (
            Path(__file__).parent.parent / "_static" / "screenshots" / "widgets" / "shots.json"
        )
        try:
            with open(index, "r") as f:
                shots = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            shots = {}

        widget_shots = shots.get(class_name.lower(), dict())
    else:
        widget_shots = {}

    widget_shots = {
        f"../../widgets/{class_name.lower()}/{k}.png": v for k, v in widget_shots.items()
    }

    context = {
        "module": module,
        "class_name": class_name,
        "class_underline": "=" * len(class_name),
        "obj": obj,
        "defaults": defaults,
        "configurable": is_configurable and issubclass(obj, configurable.Configurable),
        "commandable": is_commandable and issubclass(obj, command.base.CommandObject),
        "is_widget": is_widget,
        # "extra_arguments": arguments,
        "screen_shots": widget_shots,
        "supported_backends": is_widget and obj.supported_backends,
        "full_module": obj.__module__,
    }
    if context["commandable"]:
        context["commands"] = [
            # Command methods have the "_cmd" attribute so we check for this
            # However, some modules are Mocked so we need to exclude them
            attr.__name__
            for _, attr in inspect.getmembers(obj)
            if hasattr(attr, "_cmd") and not isinstance(attr, MagicMock)
        ]

    rst = qtile_class_template.render(**context)
    return rst
    # for line in rst.splitlines():
    #     yield line

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
import importlib
import inspect

from docs.qtile_docs.templates import qtile_commands_template
from libqtile import command
from libqtile.utils import import_class


class QtileCommands:
    """
    A custom directive that is used to display the commands exposed to
    the command graph for a given object.

    This is used to ensure the public API is up to date in our documentation.

    Any CommandObject with a command decorated with `@expose_command` will
    appear in the list of available commands.
    """

    def __init__(
        self,
        module,
        baseclass=None,
        includebase=False,
        object_node="",
        object_selector_name=False,
        object_selector_id=False,
        object_selector_string="",
        no_title=False,
        exclude_command_object_methods=False,
    ):
        self.module = module
        self.baseclass = baseclass
        self.includebase = includebase
        self.object_node = object_node
        self.object_selector_name = object_selector_name
        self.object_selector_id = object_selector_id
        self.object_selector_name = object_selector_name
        self.no_title = no_title
        self.exclude_command_object_methods = exclude_command_object_methods

    def get_class_commands(self, cls, exclude_inherited=False):
        commands = []

        for attr in dir(cls):
            # Some attributes will result in an AttributeError so we can skip them
            if not hasattr(cls, attr):
                continue

            method = getattr(cls, attr)

            # If it's not a callable method then we don't need to look at it
            if not callable(method):
                continue

            # Check if method has been exposed to the command graph
            if getattr(method, "_cmd", False):
                # If we're excluding inherited commands then check for them here
                if exclude_inherited and hasattr(command.base.CommandObject, method):
                    continue

                commands.append(attr)

        return commands

    def make_interface_syntax(self, obj):
        """
        Builds strings to show the lazy and cmd-obj syntax
        used to access the commands for the given object.
        """
        lazy = "lazy"
        cmdobj = ["qtile", "cmd-obj", "-o"]

        # Get the node on the command graph
        node = self.object_node

        if not node:
            # cmd-obj needs the root note to be specified
            cmdobj.append("cmd")
        else:
            lazy += f".{node}"
            cmdobj.append(node)

        # Give an example of an object selector
        if self.object_selector_name:
            name = obj.__name__.lower()
            lazy += f'["{name}"]'
            cmdobj.append(name)

        elif self.object_selector_id:
            lazy += "[ID]"
            cmdobj.append("[ID]")

        elif self.object_selector_name:
            selector = self.object_selector_name
            lazy += f'["{selector}"]'
            cmdobj.append(selector)

        # Add syntax to call the command
        lazy += ".<command\>()"
        cmdobj.extend(["-f", "<command\>"])

        interfaces = {"lazy": lazy, "cmdobj": " ".join(cmdobj)}

        return interfaces

    def generate(self):
        module = importlib.import_module(self.module)

        baseclass = self.baseclass or "libqtile.command.base.CommandObject"

        self.baseclass = import_class(*baseclass.rsplit(".", 1))

        rst = ""

        for item in dir(module):
            if item in ("ScreenSplit", "Wttr"):
                continue
            obj = import_class(self.module, item)

            if (
                not inspect.isclass(obj)
                or not issubclass(obj, self.baseclass)
                or (obj is self.baseclass and not self.includebase)
            ):
                continue

            commands = sorted(self.get_class_commands(obj, self.exclude_command_object_methods))

            context = {
                "objectname": f"{obj.__module__}.{obj.__name__}",
                "module": obj.__module__,
                "baseclass": obj.__name__,
                "underline": "=" * len(obj.__name__),
                "commands": commands,
                "no_title": self.no_title,
                "interfaces": self.make_interface_syntax(obj),
            }
            rst += qtile_commands_template.render(**context)

        return rst


def qtile_commands(
    module,
    baseclass=None,
    includebase=False,
    object_node="",
    object_selector_name=False,
    object_selector_id=False,
    object_selector_string="",
    no_title=False,
    exclude_command_object_methods=False,
):
    qcommand = QtileCommands(
        module,
        baseclass,
        includebase,
        object_node,
        object_selector_name,
        object_selector_id,
        object_selector_string,
        no_title,
        exclude_command_object_methods,
    )
    return qcommand.generate()

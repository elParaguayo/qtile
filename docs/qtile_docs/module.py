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

from docs.qtile_docs.qtile_class import qtile_class
from docs.qtile_docs.templates import qtile_module_template
from libqtile.utils import import_class

# class QtileModule:
#     optional_arguments = 3

#     option_spec = {
#         "baseclass": directives.unchanged,
#         "no-config": directives.flag,
#         "no-commands": directives.flag,
#         # Comma separated list of object names to skip
#         "exclude": directives.unchanged,
#     }


def qtile_module(
    module_name, baseclass_name=None, no_config=False, no_commands=False, exclude=str()
):
    module = importlib.import_module(module_name)

    baseclass = None
    if baseclass_name is not None:
        baseclass = import_class(*baseclass_name.rsplit(".", 1))

    print(dir(module))

    rst = ""

    for item in dir(module):
        if item in exclude.split(","):
            continue
        obj = import_class(module_name, item)
        if not inspect.isclass(obj) or (baseclass and not issubclass(obj, baseclass)):
            continue

        context = {
            "module": module,
            "class_name": item,
            "no_config": no_config,
            "no_commands": no_commands,
        }
        # rst += qtile_module_template.render(**context)
        rst += qtile_class(f"{module_name}.{item}", no_config=no_config, no_commands=no_commands)

    return rst

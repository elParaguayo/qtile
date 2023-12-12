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
from jinja2 import Template

qtile_commands_template = Template(
    """
{% if not no_title %}
{{ baseclass }}
{{ underline }}
{% endif %}

**API commands**

To access commands on this object via the command graph, use one of the following
options:

| `lazy` interface | `qtile cmd-obj` interface |
| ---------------- | ------------------------- |
| {{ interfaces["lazy"] }} | {{ interfaces["cmdobj"] }} |

The following commands are available for this object:

{% for cmd in commands %}
::: {{ objectname }}.{{ cmd }}
    options:
        heading_level: 0
        summary: true

{% endfor %}       
"""
)

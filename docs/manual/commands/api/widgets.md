# Widget objects

Widgets are small scripts that are used to provide content or add functionality
to the bar. Some widgets will expose commands in order for functionality to be
triggered indirectly (e.g. via a keypress).

Widgets can access the parent bar and screen via the command graph.

```python exec="1"
from docs.qtile_docs.graph import qtile_graph
from docs.qtile_docs.commands import qtile_commands
print(qtile_graph("widget"))

print(qtile_commands("libqtile.widget", baseclass="libqtile.widget.base._Widget", object_node="widget", object_selector_name=True))
```

|

.. qtile_commands:: libqtile.widget
    :baseclass: libqtile.widget.base._Widget
    :object-node: widget
    :object-selector-name:

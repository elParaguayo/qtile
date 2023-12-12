# Bar objects

The bar is primarily used to display widgets on the screen. As a result, the bar
does not need many of its own commands.

To select a bar on the command graph, you must use a selector (as there is no
default bar). The selector is the position of the bar on the screen i.e. "top",
"bottom", "left" or "right".

The bar can access the screen it's on and the widgets it contains via the command
graph.

```python exec="1"
from docs.qtile_docs.graph import qtile_graph
print(qtile_graph("bar"))
```

::: libqtile.bar.Bar

.. qtile_commands:: libqtile.bar
    :object-node: bar
    :object-selector-string: position
    :no-title:

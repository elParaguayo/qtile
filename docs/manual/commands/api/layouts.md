# Layout objects

Layouts position windows according to their specific rules. Layout commands
typically include moving windows around the layout and changing the size of windows.

Layouts can access the windows being displayed, the group holding the layout and
the screen displaying the layout.

```python exec="1"
from docs.qtile_docs.graph import qtile_graph
print(qtile_graph("layout"))
```

|

.. qtile_commands:: libqtile.layout
    :baseclass: libqtile.layout.base.Layout
    :object-node: layout

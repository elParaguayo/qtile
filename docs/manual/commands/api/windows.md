# Window objects

The size and position of windows is determined by the current layout. Nevertheless,
windows can still change their appearance in multiple ways (toggling floating state,
fullscreen, opacity).

Windows can access objects relevant to the display of the window (i.e.
the screen, group and layout).

```python exec="1"
from docs.qtile_docs.graph import qtile_graph
print(qtile_graph("window"))
```

|

.. qtile_commands:: libqtile.backend.base
    :baseclass: libqtile.backend.base.Window
    :object-node: window
    :includebase:
    :no-title:
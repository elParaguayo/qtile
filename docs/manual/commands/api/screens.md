# Screen objects

Screens are the display area that holds bars and an active group. Screen commands
include changing the current group and changing the wallpaper.

Screens can access objects displayed on that screen e.g. bar, widgets, groups, layouts
and windows.

```python exec="1"
from docs.qtile_docs.graph import qtile_graph
print(qtile_graph("screen"))
```

|

.. qtile_commands:: libqtile.config
    :baseclass: libqtile.config.Screen
    :includebase:
    :object-node: screen
    :no-title:

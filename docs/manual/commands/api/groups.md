# Group objects

Groups are Qtile's workspaces. Groups are not responsible for the positioning
of windows (that is handled by the [layouts][layouts]) so the available
commands are somewhat more limited in scope.

Groups have access to the layouts in that group, the windows in the group and
the screen displaying the group.

```python exec="1"
from docs.qtile_docs.graph import qtile_graph
print(qtile_graph("group"))
```

|

.. qtile_commands:: libqtile.group
    :baseclass: libqtile.group._Group
    :includebase:
    :object-node: group
    :no-title:
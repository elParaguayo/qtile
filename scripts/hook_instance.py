from ast import AST, literal_eval

from griffe import Extension, ObjectNode, Attribute, get_logger
from griffe.agents.inspector import Inspector, inspect


logger = get_logger(__name__)


class HookInstance(Extension):
    def on_attribute_instance(self, *, node: AST | ObjectNode, attr: Attribute) -> None:
        if isinstance(node, ObjectNode) or attr.path != "libqtile.hook.subscribe":
            return

        # rely on dynamic analysis
        inspected_hook_module = inspect(
            "hook",
            filepath=attr.filepath,
            parent=attr.parent.parent,  # libqtile
        )

        subscribe = inspected_hook_module.get_member("subscribe")
        print(subscribe.__dict__)
        attr.parent.del_member("subscribe")
        attr.parent.set_member("subscribe", subscribe)
        logger.info("Enabled inspection of hook instance.")

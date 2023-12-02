from ast import AST, literal_eval

from griffe import Extension, ObjectNode, Attribute, get_logger

logger = get_logger(__name__)


class AllWidgets(Extension):
    def on_attribute_instance(self, *, node: AST | ObjectNode, attr: Attribute) -> None:
        if isinstance(node, ObjectNode):
            return
        if attr.path == "libqtile.widget.widgets":
            if attr.parent.exports is None:
                attr.parent.exports = []
            attr.parent.exports.extend([literal_eval(key) for key in attr.value.keys])
            logger.info(f"Extended exports for {attr.parent}: {attr.parent.exports}")

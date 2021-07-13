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
import os

from libqtile.images import Img
from libqtile.log_utils import logger
from libqtile.popup.toolkit import PopupGridLayout, PopupSlider, PopupText


class PopupMenuItem(PopupText):
    defaults = [
        ("menu_icon", None, "Optional icon to display next to text"),
        ("icon_size", 12, "Size of menu icon"),
        ("icon_gap", 5, "Gap between icon and text"),
        ("show_icon", True, "Show menu icons"),
        ("toggle_box", False, "Whether to show a toggle box"),
        ("toggled", False, "Whether toggle box is toggled")
    ]

    def __init__(self, text="", **config):
        logger.warning(f"{config=}")
        PopupText.__init__(self, text, **config)
        self.add_defaults(PopupMenuItem.defaults)
        if self.menu_icon and not self.toggle_box:
            self.load_icon(self.menu_icon)
        else:
            self.icon = None

    def _configure(self, qtile, container):
        PopupText._configure(self, qtile, container)
        self.layout.width = self.width - self.icon_size - self.icon_gap

    def load_icon(self, icon):
        if isinstance(icon, bytes):
            img = Img(icon)
        elif isinstance(icon, str):

            filename = os.path.expanduser(self.menu_icon)

            if not os.path.exists(filename):
                logger.warning("Icon image does not exist: {}".format(filename))
                return

            img = Img.from_path(self.filename)

        else:
            self.icon = None
            return

        if img.width != self.icon_size:
            img.scale(width_factor=(self.icon_size / img.width), lock_aspect_ratio=True)

        self.icon = img

    def paint(self):
        self.clear(self._background)

        offset = 0

        if self.toggle_box:
            self.drawer.ctx.save()
            self.drawer.ctx.translate(0, int((self.height - self.icon_size) / 2) - 1)
            self.drawer.set_source_rgb(self.foreground)
            self.drawer.rectangle(0, 0, self.icon_size, self.icon_size, 1)
            if self.toggled:
                self.drawer.fillrect(3, 3, self.icon_size - 6, self.icon_size - 6)
            self.drawer.ctx.restore()

        if self.icon and self.show_icon:
            self.drawer.ctx.save()
            self.drawer.ctx.translate(0, int((self.height - self.icon.height) / 2))
            self.drawer.ctx.set_source(self.icon.pattern)
            self.drawer.ctx.paint()
            self.drawer.ctx.restore()
        
        if self.show_icon or self.toggle_box:
            offset = self.icon_size + self.icon_gap

        self.drawer.ctx.save()
        self.drawer.ctx.translate(offset,
                                  int((self.height - self.layout.height) / 2))
        self.layout.draw(0, 0)
        self.drawer.ctx.restore()


class PopupMenuSeparator(PopupSlider):
    defaults = [
        ("colour_above", "ff00ff", "Separator colour"),
        ("end_margin", 10, ""),
        ("marker_size", 0, "")
    ]

    def __init__(self, **config):
        PopupSlider.__init__(self, value=0, **config)
        self.add_defaults(PopupMenuSeparator.defaults)


class PopupMenu(PopupGridLayout):

    def __init__(self, qtile, controls, **config):
        PopupGridLayout.__init__(self, qtile, controls=controls, **config)
        self._hide_timer = None

    def process_pointer_enter(self, x, y):
        PopupGridLayout.process_pointer_enter(self, x, y)
        if self._hide_timer is not None:
            self._hide_timer.cancel()
            self._hide_timer = None

    def process_pointer_leave(self, x, y):
        PopupGridLayout.process_pointer_leave(self, x, y)
        self._hide_timer = self.qtile.call_later(0.5, self.kill)

    @classmethod
    def from_dbus_menu(cls, qtile, dbusmenuitems, **config):
        menuitems = []
        prev_sep = False
        row = 0
        for i, dbmitem in enumerate(dbusmenuitems):
            label = dbmitem.label.replace("_", "")
            sep = dbmitem.item_type == "separator"
            if not dbmitem.visible:
                continue

            if prev_sep and sep:
                continue

            if sep:
                menuitems.append(
                    PopupMenuSeparator(
                        row=row,
                        rowspan=1,
                        bar_size=1,
                        colour_above=config["separator_colour"]
                    )
                )
            else:
                menuitems.append(
                    PopupMenuItem(
                        row=row,
                        col=0,
                        row_span=2,
                        text=label,
                        menu_icon=dbmitem.icon_data,
                        hover=True,
                        mouse_callbacks={"Button1": lambda dbmitem=dbmitem: dbmitem.click()},
                        font_size=config["fontsize"],
                        foreground=config["foreground"],
                        highlight=config["highlight"],
                        show_icon=config["show_menu_icons"],
                        toggle_box=True if dbmitem.toggle_type else False,
                        toggled=True if dbmitem.toggle_state else False
                    )
                )
            prev_sep = sep
            row += 1 if sep else 2

        return cls.generate(qtile, menuitems, **config)

    @classmethod
    def generate(cls, qtile, menuitems, **config):
        rowcount = sum(x.row_span for x in menuitems)
        menu_config = {
            "width": 200,
            "height": 12 * rowcount + 10,
            "rows": rowcount,
            "cols": 1
        }
        menu_config.update(config)

        return cls(qtile, controls=menuitems, **menu_config)

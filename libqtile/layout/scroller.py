# Copyright (c) 2025 elParaguayo
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
from libqtile.command.base import expose_command
from libqtile.config import ScreenRect
from libqtile.layout import base
from libqtile.log_utils import logger


class Column(base._ClientList):
    """
    A helper class to contain the clients in each column of the layout
    """

    cw = base._ClientList.current_client
    current = base._ClientList.current_index

    def __init__(self, insert_position, width=100):
        base._ClientList.__init__(self)
        self.width = width
        self.insert_position = insert_position
        self.heights = {}

    @expose_command()
    def info(self):
        info = base._ClientList.info(self)
        info.update(
            dict(
                heights=[self.heights[c] for c in self.clients],
                split=True,
            )
        )
        return info

    def add_client(self, client, height=100):
        base._ClientList.add_client(self, client, self.insert_position)
        self.heights[client] = height
        delta = 100 - height
        if delta != 0:
            n = len(self)
            growth = [int(delta / n)] * n
            growth[0] += delta - sum(growth)
            for c, g in zip(self, growth):
                self.heights[c] += g

    def remove(self, client):
        base._ClientList.remove(self, client)
        client.clear_clip()
        delta = self.heights[client] - 100
        del self.heights[client]
        if delta != 0:
            n = len(self)
            growth = [int(delta / n)] * n
            growth[0] += delta - sum(growth)
            for c, g in zip(self, growth):
                self.heights[c] += g

    def __str__(self):
        cur = self.current
        return "Column: " + ", ".join(
            [
                (
                    "[%s: %d]" % (c.name, self.heights[c])
                    if c == cur
                    else "%s: %d" % (c.name, self.heights[c])
                )
                for c in self.clients
            ]
        )


class Scroller(base.Layout):
    """
    A modified version of the Columns layout.

    The screen is split into columns, each of which has its own `width`
    property. The layout can contain several columns even if they exceed the
    screen width.

    The `viewx` property allows the user to only see selective windows, and can
    be used to 'scroll' through the windows, in a sense. This is an attempt to
    mimic a similar feature present in Scrolling Window Managers like Niri.
    The `maxwidth` property imposes an upper bound on the value of `viewx`.

    Potential keybind configuration:

        Key([mod], "space", lazy.layout.next()),
        Key([mod], "h", lazy.layout.left()),
        Key([mod], "j", lazy.layout.down()),
        Key([mod], "k", lazy.layout.up()),
        Key([mod], "l", lazy.layout.right()),
        Key([mod, shift], "h", lazy.layout.shuffle_left()),
        Key([mod, shift], "j", lazy.layout.shuffle_down()),
        Key([mod, shift], "k", lazy.layout.shuffle_up()),
        Key([mod, shift], "l", lazy.layout.shuffle_right()),
        Key([mod, ctrl], "h", lazy.layout.grow_left()),
        Key([mod, ctrl], "j", lazy.layout.grow_down()),
        Key([mod, ctrl], "k", lazy.layout.grow_up()),
        Key([mod, ctrl], "l", lazy.layout.grow_right()),
        Key([mod, ctrl, shift], "h", lazy.layout.scroll_left()),
        Key([mod, ctrl, shift], "l", lazy.layout.scroll_right()),

    """

    defaults = [
        ("border_width", 0, "Border width"),
        ("border_focus", "ffffff", "Border colour of focused window"),
        ("border_normal", "000000", "Border colour of unfocused window"),
        ("default_width", 50, "Default window width"),
        ("margin", 0, "Margin between windows"),
        ("width_rules", {}, "Rules for setting custom width"),
    ]

    def __init__(self, **config):
        base.Layout.__init__(self, **config)
        self.add_defaults(Scroller.defaults)
        self.current = 0
        self.viewx = 0
        self.maxwidth = self.default_width
        self.columns = [Column(0, self.default_width)]
        self.pw = 0

    @property
    def cc(self):
        """Current column"""
        return self.columns[self.current]

    def clone(self, group):
        c = base.Layout.clone(self, group)
        c.current = 0
        c.viewx = 0
        c.maxwidth = self.default_width
        c.columns = [Column(0, self.default_width)]
        return c

    @expose_command()
    def info(self):
        d = base.Layout.info(self)
        d["clients"] = []
        d["columns"] = []
        for c in self.columns:
            cinfo = c.info()
            d["clients"].extend(cinfo["clients"])
            d["columns"].append(cinfo)
        d["current"] = self.current
        return d

    def focus(self, client):
        """
        Focus the specified client.
        Do not update the viewx property since it is only meant to be scrolled.
        """
        for i, c in enumerate(self.columns):
            if client in c:
                c.focus(client)
                self.current = i
                break

    def hide(self):
        for column in self.columns:
            for client in column:
                client.clear_clip()

    def add_column(self, width):
        """
        Add a new column of given width, and increase `maxwidth` accordingly
        """
        c = Column(-1, width)
        self.maxwidth += width
        self.columns.append(c)
        self.focus(self.cc.cw)
        return c

    def remove_column(self, col):
        """
        Remove the specified column and reduce `maxwidth` accordingly.
        """
        if len(self.columns) == 1:
            logger.error("Can't remove last column")
            return

        idx = self.columns.index(col)
        self.maxwidth -= col.width
        del self.columns[idx]
        if idx <= self.current:
            self.current = max(0, self.current - 1)
            self.focus(self.cc.cw)

    def get_width(self, client):
        """
        Check among user-given rules to determine column width.
        If nothing is provided, `self.default_width` is used.
        """
        for match, width in self.width_rules.items():
            if client.match(match):
                return width
        return self.default_width

    def add_client(self, client):
        c = self.cc
        c.add_client(client)

    def remove(self, client):
        remove = False
        for c in self.columns:
            if client in c:
                c.remove(client)
                if len(c) == 0 and len(self.columns) > 1:
                    remove = True
                break
        if remove:
            self.remove_column(c)
        return self.columns[self.current].cw

    def configure(self, client, screen_rect):
        """
        Place windows on the screen.

        Every window that should be visible given the current `viewx` and
        dimensions, is placed; the rest are hidden.
        posx, posy, viewx, widths and heights are in percentages of screen
        dimensions.
        """
        border = self.border_width
        margin_size = (
            [self.margin] * 4 if isinstance(self.margin, int) else self.margin
        )

        screenx = screen_rect.x + margin_size[3]
        screeny = screen_rect.y + margin_size[0]
        screenh = screen_rect.height - (margin_size[0] + margin_size[2])
        screenw = screen_rect.width - (margin_size[1] + margin_size[3])

        drawable_rect = ScreenRect(screenx, screeny, screenw, screenh)

        posx = -self.viewx
        for col in self.columns:
            if client in col:
                break
            posx += col.width
        else:
            client.hide()
            return

        posy = 0
        for c in col:
            if client == c:
                break
            posy += col.heights[c]

        if client.has_focus:
            color = self.border_focus
        else:
            color = self.border_normal

        width = int(0.5 + col.width * screen_rect.width * 0.01)
        x = screen_rect.x + int(0.5 + posx * screen_rect.width * 0.01)

        height = int(0.5 + col.heights[client] * screen_rect.height * 0.01 / len(col))
        y = screen_rect.y + int(0.5 + posy * screen_rect.height * 0.01 / len(col))

        win_rect = ScreenRect(
            x + margin_size[3],
            y + margin_size[0],
            width - 2 * border - (margin_size[1] + margin_size[3]),
            height - 2 * border - (margin_size[0] + margin_size[2]),
        )

        # If some part of the window is visible, place it
        intersection = win_rect.intersects(drawable_rect)
        client.clear_clip()
        if intersection:
            w, h = width - 2 * border, height - 2 * border
            # win_x = x + margin_size[3]
            # win_w = w - (margin_size[1] + margin_size[3])
            clip = False
            if client.height != win_rect.height:
                client.place(x, y, w, h, border, color, margin=margin_size)

            if win_rect.x < screenx:
                clip = True
                clipx = screenx - win_rect.x - border
                clipw = win_rect.width - clipx
            elif (win_rect.x + win_rect.width) > (screenx + screenw):
                clip = True
                x -= border
                clipx = 0
                clipw = win_rect.width - ((win_rect.width + win_rect.x) - screenw) + 2 * border
                
                if clipw < 0:
                    clipw = 0
            else:
                client.clear_clip()

            if clip:
                client.set_clip(clipx, screeny, clipw, screenh, border)

            client.place(x, y, w, h, border, color, margin=margin_size)
            client.unhide()
        else:
            client.hide()

    def focus_first(self):
        if self.columns:
            return self.columns[0].focus_first()
        return None

    def focus_last(self):
        if self.columns:
            return self.columns[-1].focus_last()
        return None

    def focus_next(self, win):
        """Same as in Columns."""
        for idx, col in enumerate(self.columns):
            if win in col:
                if nxt := col.focus_next(win):
                    return nxt
                break
        if idx + 1 < len(self.columns):
            return self.columns[idx + 1].focus_first()
        return None

    def focus_previous(self, win):
        """Same as in Columns."""
        for idx, col in enumerate(self.columns):
            if win in col:
                if prev := col.focus_previous(win):
                    return prev
                break
        if idx > 0:
            return self.columns[idx - 1].focus_last()
        return None

    @expose_command()
    def left(self):
        """Get the last active window of the column to the left."""
        if self.current > 0:
            self.current = self.current - 1
        self.group.focus(self.cc.cw, True)

    @expose_command()
    def right(self):
        """Get the last active window of the column to the right."""
        if len(self.columns) - 1 > self.current:
            self.current = self.current + 1
        self.group.focus(self.cc.cw, True)

    @expose_command()
    def up(self):
        """Get the window above the active one."""
        col = self.cc
        if col.current_index > 0:
            col.current_index -= 1
        self.group.focus(col.cw, True)

    @expose_command()
    def down(self):
        """Get the window below the active one."""
        col = self.cc
        if col.current_index < len(col) - 1:
            col.current_index += 1
        self.group.focus(col.cw, True)

    @expose_command()
    def next(self) -> None:
        """Get the next window."""
        if self.columns:
            self.current = (self.current + 1) % len(self.columns)
            self.cc.current = 0
        self.group.focus(self.cc.cw, True)

    @expose_command()
    def previous(self) -> None:
        """Get the previous window."""
        if self.columns:
            self.current = (self.current - 1) % len(self.columns)
            self.cc.current = len(self.cc) - 1
        self.group.focus(self.cc.cw, True)

    @expose_command()
    def shuffle_left(self):
        """Same as in Columns."""
        cur = self.cc
        client = cur.cw
        if client is None:
            return
        if self.current > 0:
            self.current -= 1
            new = self.cc
            new.add_client(client, cur.heights[client])
            cur.remove(client)
            if len(cur) == 0:
                self.remove_column(cur)
        elif len(cur) > 1:
            new = self.add_column(self.get_width(client))
            new.add_client(client, cur.heights[client])
            cur.remove(client)
            self.current = 0
        else:
            return
        self.group.layout_all()

    @expose_command()
    def shuffle_right(self):
        """Same as in Columns."""
        cur = self.cc
        client = cur.cw
        if client is None:
            return
        if self.current + 1 < len(self.columns):
            self.current += 1
            new = self.cc
            new.add_client(client, cur.heights[client])
            cur.remove(client)
            if len(cur) == 0:
                self.remove_column(cur)
        elif len(cur) > 1:
            new = self.add_column(self.get_width(client))
            new.add_client(client, cur.heights[client])
            cur.remove(client)
            self.current = len(self.columns) - 1
        else:
            return
        self.group.layout_all()

    @expose_command()
    def shuffle_up(self):
        """Same as in Columns."""
        if self.cc.current_index > 0:
            self.cc.shuffle_up()
            self.group.layout_all()

    @expose_command()
    def shuffle_down(self):
        """Same as in Columns."""
        if self.cc.current_index + 1 < len(self.cc):
            self.cc.shuffle_down()
            self.group.layout_all()

    @expose_command()
    def shrink_left(self):
        """
        Not the same as in Columns.
        Shrink the column leftwards without affecting other windows.
        """
        if self.cc.width > self.grow_amount:
            self.cc.width -= self.grow_amount
            self.group.layout_all()

    @expose_command()
    def grow_right(self):
        """
        Not the same as in Columns.
        Grow the column rightwards without affecting other windows.
        """
        self.cc.width += self.grow_amount
        self.group.layout_all()

    @expose_command()
    def grow_down(self):
        """
        Similar to Columns.
        Grow the window downwards and shrink the next/previous window.
        """
        col = self.cc
        if col.current + 1 < len(col):
            if col.heights[col[col.current + 1]] > self.grow_amount:
                col.heights[col[col.current + 1]] -= self.grow_amount
                col.heights[col.cw] += self.grow_amount
                self.group.layout_all()
        elif len(col) > 1:
            if col.heights[col.cw] > self.grow_amount:
                col.heights[col[col.current - 1]] += self.grow_amount
                col.heights[col.cw] -= self.grow_amount
                self.group.layout_all()

    @expose_command()
    def shrink_up(self):
        """
        Similar to Columns.
        Shrink the window upwards and grow the next/previous window.
        """
        col = self.cc
        if col.current < len(col) - 1:
            if col.heights[col.cw] > self.grow_amount:
                col.heights[col.cw] -= self.grow_amount
                col.heights[col[col.current + 1]] += self.grow_amount
                self.group.layout_all()
        elif len(col) > 1:
            if col.heights[col.cw] > self.grow_amount:
                col.heights[col.cw] -= self.grow_amount
                col.heights[col[col.current - 1]] += self.grow_amount
                self.group.layout_all()

    @expose_command()
    def scroll_right(self):
        """
        The USP of this layout.
        'Scrolls' the 'view' by 5% of the screen to the right up to maxwidth.
        """
        if self.viewx < self.maxwidth:
            self.viewx += 5
        self.group.focus(self.cc.cw)

    @expose_command()
    def scroll_left(self):
        """
        The USP of this layout.
        'Scrolls' the 'view' by 5% of the screen to the left up to 0.
        """
        if self.viewx > 0:
            self.viewx -= 5
        self.group.focus(self.cc.cw)

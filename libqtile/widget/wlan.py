# Copyright (c) 2012 Sebastian Bechtel
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sebastian Kricner
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2014 Craig Barnes
# Copyright (c) 2015 farebord
# Copyright (c) 2015 Jörg Thalheim (Mic92)
# Copyright (c) 2016 Juhani Imberg
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
import re
import subprocess

try:
    import iwlib

    HAS_IWLIB = True
except ModuleNotFoundError:
    HAS_IWLIB = False

from libqtile.confreader import ConfigError
from libqtile.log_utils import logger
from libqtile.pangocffi import markup_escape_text
from libqtile.widget import base

RE_SSID = re.compile(r"^SSID: (.*)$")  # assumes 'SSID' label is constant across languages
RE_STRENGTH = re.compile(
    r"^\S+: (-.*) dBm$"
)  # just look for a dBm value to avoid language differences


def convert_strength_string(strength):
    value = int(strength)
    return int(value + 110)


def get_status(interface_name):
    interface = iwlib.get_iwconfig(interface_name)
    if "stats" not in interface:
        return None, None
    quality = interface["stats"]["quality"]
    essid = bytes(interface["ESSID"]).decode()
    return essid, quality


def get_iw_status(interface_name):
    cmd = ["iw", "dev", interface_name, "link"]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    ssid = ""
    strength = ""
    for line in proc.stdout.decode().split("\n"):
        text = line.strip()
        _ssid = RE_SSID.match(text)
        _strength = RE_STRENGTH.match(text)

        if not ssid and _ssid:
            ssid = _ssid.group(1)
        elif not strength and _strength:
            strength = _strength.group(1)

        if ssid and strength:
            break

    else:
        if ssid or strength:
            logger.warning(
                "Could not retrieve both ssid and strength data from iw. ssid=%s, strength=%s",
                ssid,
                strength,
            )
        return None, None

    try:
        quality = convert_strength_string(strength)
    except ValueError:
        logger.error("Unexpected strength value: %s", strength)
        return ssid, 0

    return ssid, quality


class Wlan(base.InLoopPollText):
    """
    Displays Wifi SSID and quality.

    .. important::

        Currently, the widget relies on iwlib_ to get this data. However, this library
        relies on ``wireless-tools`` which is an unmaintained package. Distros are moving
        towards using ``iw`` instead. This widget can also parse the output of ``iw`` by
        setting ``use_iw=True``. Support for ``iwlib`` is likely to be removed in future
        releases.

    .. _iwlib: https://pypi.org/project/iwlib/
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("interface", "wlan0", "The interface to monitor"),
        (
            "ethernet_interface",
            "eth0",
            "The ethernet interface to monitor, NOTE: If you do not have a wlan device in your system, ethernet functionality will not work, use the Net widget instead",
        ),
        ("use_iw", False, "Get SSID and signal strength by parsing output from ``iw``"),
        ("update_interval", 1, "The update interval."),
        ("disconnected_message", "Disconnected", "String to show when the wlan is diconnected."),
        ("ethernet_message", "eth", "String to show when ethernet is being used"),
        (
            "use_ethernet",
            False,
            "Activate or deactivate checking for ethernet when no wlan connection is detected",
        ),
        (
            "format",
            "{essid} {quality}/70",
            'Display format. For percents you can use "{essid} {percent:2.0%}"',
        ),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Wlan.defaults)
        self.ethernetInterfaceNotFound = False

    def _configure(self, qtile, bar):
        if not self.use_iw and not HAS_IWLIB:
            raise ConfigError(
                "iwlib module is not installed. Install module or set 'use_iw=True'."
            )
        base.InLoopPollText._configure(self, qtile, bar)

    def poll(self):
        try:
            if self.use_iw:
                try:
                    essid, quality = get_iw_status(self.interface)
                except subprocess.CalledProcessError:
                    logger.error("Could not get wifi status. Error opening iw.")
                    essid, quality = None, None
            else:
                essid, quality = get_status(self.interface)
            disconnected = essid is None
            if disconnected:
                if self.use_ethernet:
                    try:
                        with open(
                            f"/sys/class/net/{self.ethernet_interface}/operstate"
                        ) as statfile:
                            if statfile.read().strip() == "up":
                                return self.ethernet_message
                            else:
                                return self.disconnected_message
                    except FileNotFoundError:
                        if not self.ethernetInterfaceNotFound:
                            logger.error("Ethernet interface has not been found!")
                            self.ethernetInterfaceNotFound = True
                        return self.disconnected_message
                else:
                    return self.disconnected_message
            return self.format.format(
                essid=markup_escape_text(essid), quality=quality, percent=(quality / 70)
            )
        except OSError:
            logger.error(
                "Probably your wlan device is switched off or "
                " otherwise not present in your system."
            )

#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Gepeto.
#
# Gepeto is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gepeto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gepeto; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from gettext import translation
import os

__all__ = ["sysconf", "iface", "Error", "_"]

class Error(Exception): pass

try:
    _ = translation("gepeto").ugettext
except IOError:
    _ = lambda s: unicode(s)

class Proxy:
    def __init__(self, object=None):
        self.object = object
    def __getattr__(self, attr):
        return getattr(self.object, attr)
    def __repr__(self):
        return "<Proxy for '%s'>" % repr(self.object)

sysconf = Proxy()
iface = Proxy()

def init(opts=None):
    from gepeto.const import DEBUG, INFO, WARNING, ERROR, CONFFILE, DISTROFILE
    from gepeto.interface import createInterface
    from gepeto.sysconfig import SysConfig
    from gepeto.interface import Interface
    from gepeto.control import Control

    sysconf.object = SysConfig()
    if opts and opts.log_level:
        level = {"error": ERROR, "warning": WARNING,
                 "debug": DEBUG, "info": INFO}.get(opts.log_level)
        if level is None:
            raise Error, "unknown log level"
        sysconf.set("log-level", level, soft=True)
    if opts and opts.data_dir:
        datadir = os.path.expanduser(opts.data_dir)
        sysconf.set("data-dir", datadir, soft=True)
    ctrl = Control(opts and opts.config_file)
    if opts.gui:
        ifacename = sysconf.get("default-gui", "gtk")
    elif opts and opts.interface:
        ifacename = opts.interface
    else:
        ifacename = "text"
    iface.object = createInterface(ifacename, not bool(opts.command))
    if os.path.isfile(DISTROFILE):
        execfile(DISTROFILE, {"ctrl": ctrl, "iface": iface,
                              "sysconf": sysconf})
    return ctrl

# vim:ts=4:sw=4:et

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

from gepeto.hook import Hooks
hooks = Hooks()

__all__ = ["sysconf", "iface", "hooks", "Error", "_"]

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
    from gepeto.const import DEBUG, INFO, WARNING, ERROR, DISTROFILE
    from gepeto.interface import createInterface
    from gepeto.sysconfig import SysConfig
    from gepeto.interface import Interface
    from gepeto.control import Control

    sysconf.object = SysConfig()
    if opts:
        if opts.log_level:
            level = {"error": ERROR, "warning": WARNING,
                     "debug": DEBUG, "info": INFO}.get(opts.log_level)
            if level is None:
                raise Error, "unknown log level"
            sysconf.set("log-level", level, soft=True)
        if opts.data_dir:
            datadir = os.path.expanduser(opts.data_dir)
            sysconf.set("data-dir", datadir, soft=True)
    ctrl = Control(opts and opts.config_file)
    if opts:
        if opts.gui:
            ifacename = sysconf.get("default-gui", "gtk")
        elif opts.shell:
            ifacename = sysconf.get("default-shell", "text")
            if opts.command:
                raise Error, "Can't use commands with shell interfaces"
        elif opts.interface:
            ifacename = opts.interface
        elif opts.command:
            ifacename = "text"
        else:
            raise Error, "No interface selected"
    else:
        ifacename = "text"
    iface.object = createInterface(ifacename, ctrl,
                                   not bool(opts and opts.command))

    # Import every plugin, and let they do whatever they want.
    from gepeto import plugins
    pluginsdir = os.path.dirname(plugins.__file__)
    for entry in os.listdir(pluginsdir):
        if entry != "__init__.py" and entry.endswith(".py"):
            __import__("gepeto.plugins."+entry[:3])
        else:
            entrypath = os.path.join(pluginsdir, entry)
            if os.path.isdir(entrypath):
                initpath = os.path.join(entrypath, "__init__.py")
                if os.path.isfile(initpath):
                    __import__("gepeto.plugins."+entry)

    # Run distribution script, if available.
    if os.path.isfile(DISTROFILE):
        execfile(DISTROFILE, {"ctrl": ctrl, "iface": iface,
                              "sysconf": sysconf, "hooks": hooks})

    return ctrl


# vim:ts=4:sw=4:et

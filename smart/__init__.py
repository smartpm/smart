#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from gettext import translation
from smart.hook import Hooks
import os

__all__ = ["sysconf", "iface", "hooks", "Error", "_"]

class Error(Exception): pass

try:
    _ = translation("smart").ugettext
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
hooks = Hooks()

def init(command=None, argv=None,
         datadir=None, configfile=None,
         gui=False, shell=False, interface=None,
         forcelocks=False, loglevel=None):
    from smart.const import DEBUG, INFO, WARNING, ERROR, DISTROFILE
    from smart.interface import Interface, createInterface
    from smart.sysconfig import SysConfig
    from smart.interface import Interface
    from smart.control import Control

    iface.object = Interface(None)
    sysconf.object = SysConfig()
    if loglevel:
        level = {"error": ERROR, "warning": WARNING,
                 "debug": DEBUG, "info": INFO}.get(loglevel)
        if level is None:
            raise Error, "unknown log level"
        sysconf.set("log-level", level, soft=True)
    if datadir:
        sysconf.set("data-dir", os.path.expanduser(datadir), soft=True)
    ctrl = Control(configfile, forcelocks)
    if gui:
        ifacename = sysconf.get("default-gui", "gtk")
    elif shell:
        ifacename = sysconf.get("default-shell", "text")
        if command:
            raise Error, "Can't use commands with shell interfaces"
    elif interface:
        ifacename = interface
    else:
        ifacename = "text"
    iface.object = createInterface(ifacename, ctrl, command, argv)

    # Import every plugin, and let they do whatever they want.
    from smart import plugins
    pluginsdir = os.path.dirname(plugins.__file__)
    for entry in os.listdir(pluginsdir):
        if entry != "__init__.py" and entry.endswith(".py"):
            __import__("smart.plugins."+entry[:3])
        else:
            entrypath = os.path.join(pluginsdir, entry)
            if os.path.isdir(entrypath):
                initpath = os.path.join(entrypath, "__init__.py")
                if os.path.isfile(initpath):
                    __import__("smart.plugins."+entry)

    # Run distribution script, if available.
    if os.path.isfile(DISTROFILE):
        execfile(DISTROFILE, {"ctrl": ctrl, "iface": iface,
                              "sysconf": sysconf, "hooks": hooks})

    return ctrl


# vim:ts=4:sw=4:et

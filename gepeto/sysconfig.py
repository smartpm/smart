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
from gepeto.const import DATADIR, INFO
from gepeto import *
import cPickle
import os

class SysConfig(object):

    def __init__(self):
        self._map = {}
        self._weakmap = {}
        self._softmap = {}
        self.set("log-level", INFO, weak=True)
        self.set("data-dir", os.path.expanduser(DATADIR), weak=True)

    def getMap(self):
        return self._map

    def getWeakMap(self):
        return self._weakmap

    def getSoftMap(self):
        return self._softmap

    def load(self, filepath):
        filepath = os.path.expanduser(filepath)
        if not os.path.isfile(filepath):
            raise Error, "file not found: %s" % filepath
        file = open(filepath)
        self._map.clear()
        try:
            self._map.update(cPickle.load(file))
        except:
            if os.path.isfile(filepath+".old"):
                file.close()
                file = open(filepath+".old")
                self._map.update(cPickle.load(file))
        file.close()

    def save(self, filepath):
        filepath = os.path.expanduser(filepath)
        if os.path.isfile(filepath):
            os.rename(filepath, filepath+".old")
        dirname = os.path.dirname(filepath)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        file = open(filepath, "w")
        cPickle.dump(self._map, file, 2)
        file.close()

    def get(self, option, default=None, setdefault=None):
        if setdefault is not None:
            return self._map.setdefault(option, setdefault)
        value = self._softmap.get(option)
        if value is None:
            value = self._map.get(option)
            if value is None:
                value = self._weakmap.get(option, default)
        return value

    def set(self, option, value, weak=False, soft=False):
        if soft:
            self._softmap[option] = value
        elif weak:
            self._weakmap[option] = value
        else:
            self._map[option] = value
            if option in self._softmap:
                del self._softmap[option]

    def remove(self, option):
        if option in self._map:
            del self._map[option]
        if option in self._weakmap:
            del self._weakmap[option]
        if option in self._softmap:
            del self._weakmap[option]

    def setFlag(self, flag, name, relation=None, version=None):
        flags = self.get("package-flags", setdefault={})
        names = flags.get(flag)
        if names:
            lst = names.get(name)
            if lst:
                if (relation, version) not in lst:
                    lst.append((relation, version))
            else:
                names[name] = [(relation, version)]
        else:
            flags[flag] = {name: [(relation, version)]}

    def clearFlag(self, flag, name=None, relation=None, version=None):
        flags = self.get("package-flags", {})
        if flag not in flags:
            return
        if not name:
            del flags[flag]
            return
        names = flags.get(flag)
        lst = names.get(name)
        if lst is not None:
            try:
                lst.remove((relation, version))
            except ValueError:
                pass
            if not lst:
                del names[name]
        if not names:
            del flags[flag]

    def testFlag(self, flag, pkg):
        names = self.get("package-flags", {}).get(flag)
        if names:
            lst = names.get(pkg.name)
            if lst:
                for item in lst:
                    if pkg.matches(*item):
                        return True
        return False

    def filterByFlag(self, flag, pkgs):
        fpkgs = []
        names = self.get("package-flags", {}).get(flag)
        if names:
            for pkg in pkgs:
                lst = names.get(pkg.name)
                if lst:
                    for item in lst:
                        if pkg.matches(*item):
                            fpkgs.append(pkg)
                            break
        return fpkgs

    def getPriority(self, pkg):
        priority = None
        priorities = self.get("package-priorities", {}).get(pkg.name)
        if priorities:
            priority = None
            for loader in pkg.loaders:
                inchannel = priorities.get(loader.getChannel().getAlias())
                if (inchannel is not None and priority is None or
                    inchannel > priority):
                    priority = inchannel
            if priority is None:
                priority = priorities.get(None)
        return priority

    def setPriority(self, name, channelalias, priority):
        priorities = self.get("package-priorities", setdefault={})
        priorities.setdefault(name, {})[channelalias] = priority

try:
    import psyco
except ImportError:
    pass
else:
    psyco.bind(SysConfig.getPriority)

# vim:ts=4:sw=4:et


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
from gepeto import *
import random

class MirrorSystem(object):

    HISTORYSIZE = 100

    def __init__(self):
        self._mirrors = sysconf.get("mirrors", setdefault={})
        self._history = sysconf.get("mirrors-history", setdefault=[])
        self._changed = True
        self._penality = {}

    def addInfo(self, mirror, **info):
        if mirror:
            self._changed = True
            self._history.insert(0, (mirror, info))
            del self._history[self.HISTORYSIZE:]

    def get(self, url): 
        elements = {}
        for origin in self._mirrors:
            if url.startswith(origin):
                elements[origin] = MirrorElement(self, origin, origin)
                for mirror in self._mirrors[origin]:
                    elements[mirror] = MirrorElement(self, origin, mirror)
        if elements:
            elements = elements.values()
        else:
            elements = [MirrorElement(self, "", "")]
        return MirrorItem(self, url, elements)

    def updatePenality(self):
        if not self._changed:
            return
        self._changed = False
        self._penality.clear()
        data = {}
        for mirror, info in self._history:
            if mirror not in data:
                mirrordata = data.setdefault(mirror, {"size": 0, "time": 0,
                                                      "failed": 0})
            else:
                mirrordata = data[mirror]
            mirrordata["size"] += info.get("size", 0)
            mirrordata["time"] += info.get("time", 0)
            mirrordata["failed"] += info.get("failed", 0)
        for mirror in data:
            mirrordata = data[mirror]
            penality = 0
            if mirrordata["size"] and mirrordata["time"] >= 1:
                penality += (mirrordata["size"]/1000000.)/ \
                             float(mirrordata["time"])
            penality += mirrordata["failed"]
            if penality:
                self._penality[mirror] = penality

class MirrorElement(object):

    def __init__(self, system, origin, mirror):
        self._system = system
        self.origin = origin
        self.mirror = mirror

    def __cmp__(self, other):
        penal = self._system._penality
        return cmp(penal.get(self.mirror, 0), penal.get(other.mirror, 0))

class MirrorItem(object):

    def __init__(self, system, url, elements):
        self._system = system
        self._url = url
        self._elements = elements
        self._current = None

    def addInfo(self, **info):
        if self._current:
            self._system.addInfo(self._current.mirror, **info)

    def getNext(self):
        if self._elements:
            self._system.updatePenality()
            random.shuffle(self._elements)
            self._elements.sort()
            self._current = elem = self._elements.pop(0)
            return elem.mirror+self._url[len(elem.origin):]
        else:
            self._current = None
            return None

# vim:ts=4:sw=4:et

#
# Copyright (c) 2005 Conectiva, Inc.
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
from smart.util.strtools import globdistance
from smart.cache import Provides
from smart import *
import fnmatch
import re

def _stripeol(pattern):
    if pattern.endswith("$"):
         pattern = pattern[:-1]
    elif pattern.endswith('\Z(?ms)'):
        pattern = pattern[:-7]
    return pattern

class Searcher(object):
    """
    The search mechanism is smart is accessed mainly by giving a
    Searcher instance to the cache.search() method.
    
    Internally, the searching may go through different paths depending
    on the kind of information being looked for. More specifically:

    - nameversion is matched in Package.search(), so that backends
      may implement their own details in the searching mechanism.

    - provides is matched in Provides.search(), for the same reason.

    - requires, recommends, upgrades, and conflicts don't have special
      searching methods. Instead, their usual match() method is given
      an instance of the Provides type.

    - group, path, url, and other information which is found by
      PackageInfo, is searched by the Loader.search() method and
      the overloaded methods in Loader's subclasses. This ensures
      that Loaders are able to speedup the searching process, since
      many times it's necessary to access huge sequential files for
      looking up information.
    """

    def __init__(self):
        self._results = {}
        self.nameversion = []
        self.provides = []
        self.requires = []
        self.recommends = []
        self.upgrades = []
        self.conflicts = []
        self.path = []
        self.url = []
        self.group = []
        self.summary = []
        self.description = []
        self.ignorecase = True

    def reset(self):
        self._results.clear()
        del self.nameversion[:]
        del self.provides[:]
        del self.requires[:]
        del self.recommends[:]
        del self.upgrades[:]
        del self.conflicts[:]
        del self.path[:]
        del self.url[:]
        del self.group[:]
        del self.summary[:]
        del self.description[:]

    def addResult(self, obj, ratio=1.0):
        results = self._results
        if obj not in results or ratio > results[obj]:
            results[obj] = ratio

    def getResult(self, obj, default=None):
        return self._results.get(obj, default)

    def getResults(self):
        results = self._results
        lst = [(results[obj], obj) for obj in results]
        lst.sort()
        lst.reverse()
        return lst

    def getBestResults(self):
        results = self._results
        lst = [(results[obj], obj) for obj in results]
        if lst:
            lst.sort()
            lst.reverse()
            best = lst[0][0]
            lst = [x for x in lst if x[0] == best]
        return lst

    def searchCache(self, cache):
        for loader in cache.getLoaders():
            loader.search(self)

    def searchPackage(self, pkg):
        pkg.search(self)

    def addAuto(self, s, cutoff=1.0):
        if not s: return
        if s.startswith("provides:"):
            self.addProvides(s[9:], cutoff)
        elif s.startswith("requires:"):
            self.addRequires(s[9:])
        elif s.startswith("recommends:"):
            self.addRecommends(s[11:])
        elif s.startswith("upgrades:"):
            self.addUpgrades(s[9:])
        elif s.startswith("conflicts:"):
            self.addConflicts(s[10:])
        elif s.startswith("url:"):
            self.addURL(s[4:], cutoff)
        elif s.startswith("path:"):
            self.addPath(s[5:], cutoff)
        elif s.startswith("group:"):
            self.addGroup(s[6:])
        elif s.startswith("summary:"):
            self.addSummary(s[8:])
        elif s.startswith("descr:"):
            self.addDescription(s[6:])
        elif s.startswith("description:"):
            self.addDescription(s[12:])
        elif s.startswith("name:"):
            self.addNameVersion(s[5:], cutoff)
        elif s[0] == "/":
            self.addPath(s, cutoff)
        elif ":/" in s:
            self.addURL(s, cutoff)
        else:
            self.addNameVersion(s, cutoff)

    def hasAutoMeaning(self, s):
        return s and (
                s.startswith("provides:") or
                s.startswith("requires:") or
                s.startswith("recommends:") or
                s.startswith("upgrades:") or
                s.startswith("conflicts:") or
                s.startswith("url:") or
                s.startswith("path:") or
                s.startswith("group:") or
                s.startswith("summary:") or
                s.startswith("descr:") or
                s.startswith("description:") or
                s.startswith("name:") or
                s[0] == "/" or ":/" in s
            )

    def addNameVersion(self, s, cutoff=1.0):
        self.nameversion.append((s, cutoff))

    def addProvides(self, s, cutoff=1.0):
        self.provides.append((s.replace("=", "-"), cutoff))

    def _buildProvides(self, s):
        tokens = s.split("=")
        if len(tokens) == 2:
            prv = Provides(*tokens)
        elif len(tokens) == 1:
            prv = Provides(tokens[0], None)
        else:
            raise Error, _("Invalid string")
        return prv

    def addRequires(self, s):
        self.requires.append(self._buildProvides(s))

    def addRecommends(self, s):
        self.recommends.append(self._buildProvides(s))

    def addUpgrades(self, s):
        self.upgrades.append(self._buildProvides(s))

    def addConflicts(self, s):
        self.conflicts.append(self._buildProvides(s))

    def needsPackageInfo(self):
        return bool(self.group or self.path or self.url or
                    self.summary or self.description)

    def addPath(self, s, cutoff=1.0):
        self.path.append((s, cutoff))

    def addURL(self, s, cutoff=1.0):
        self.url.append((s, cutoff))

    def addGroup(self, s):
        s = _stripeol(fnmatch.translate(s)).replace("\ ", " ")
        p = re.compile("\s+".join(s.split()), self.ignorecase and re.I or 0)
        self.group.append(p)

    def addSummary(self, s):
        s = _stripeol(fnmatch.translate(s)).replace("\ ", " ")
        p = re.compile("\s+".join(s.split()), self.ignorecase and re.I or 0)
        self.summary.append(p)

    def addDescription(self, s):
        s = _stripeol(fnmatch.translate(s)).replace("\ ", " ")
        p = re.compile("\s+".join(s.split()), self.ignorecase and re.I or 0)
        self.description.append(p)

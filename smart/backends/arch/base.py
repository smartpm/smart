#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# Archlinux module written by Cody Lee (aka. platinummonkey) <platinummonkey@archlinux.us>
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
from smart.backends.arch.pm import ArchPackageManager
from archver import checkdep, vercmp, splitrelease
from smart.util.strtools import isGlob
from smart.cache import *
import fnmatch
import string
import os, re

__all__ = ["ArchPackage", "ArchProvides", "ArchRequires", "ArchUpgrades",
           "ArchConflicts"]

class ArchPackage(Package):

    __slots__ = ()

    packagemanager = ArchPackageManager

    def coexists(self, other):
        if not isinstance(other, ArchPackage):
            return True
        return False

    def matches(self, relation, version):
        if not relation:
            return True
        return checkdep(self.version, relation, version)

    def search(self, searcher):
        myname = self.name
        myversion = self.version
        ratio = 0
        ic = searcher.ignorecase
        for nameversion, cutoff in searcher.nameversion:
            _, ratio1 = globdistance(nameversion, myname, cutoff, ic)
            _, ratio2 = globdistance(nameversion,
                                     "%s-%s" % (myname, myversion), cutoff, ic)
            _, ratio3 = globdistance(nameversion, "%s-%s" %
                                     (myname, splitrelease(myversion)[0]),
                                     cutoff, ic)
            ratio = max(ratio, ratio1, ratio2, ratio3)
        if ratio:
            searcher.addResult(self, ratio)

    def __lt__(self, other):
        rc = cmp(self.name, other.name)
        if type(other) is ArchPackage:
            if rc == 0 and self.version != other.version:
                rc = vercmp(self.version, other.version)
        return rc == -1

class ArchProvides(Provides): __slots__ = ()

class ArchDepends(Depends):

    __slots__ = ()

    def matches(self, prv):
        if not isinstance(prv, ArchProvides) and type(prv) is not Provides:
            return False
        if not self.version or not prv.version:
            return True
        return checkdep(prv.version, self.relation, self.version)

class ArchRequires(ArchDepends,Requires): __slots__ = ()

class ArchUpgrades(ArchDepends,Upgrades): __slots__ = ()

class ArchConflicts(ArchDepends,Conflicts): __slots__ = ()

def enablePsyco(psyco):
    psyco.bind(ArchPackage.coexists)
    psyco.bind(ArchPackage.matches)
    psyco.bind(ArchPackage.search)
    psyco.bind(ArchPackage.__lt__)
    psyco.bind(ArchDepends.matches)

hooks.register("enable-psyco", enablePsyco)

# vim:ts=4:sw=4:et

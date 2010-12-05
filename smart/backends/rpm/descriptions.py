#
# Copyright (c) 2005 Canonical
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Anders F Bjorklund <afb@users.sourceforge.net>
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
from smart.backends.rpm.base import *

from smart import *

class RPMDescriptions:

    def __init__(self, filename):
        self._filename = filename
        self._flagdict = {}
        self._details = {}

    def load(self):
        try:
            flagdict = {}
            packages = []
            in_pre = in_description = False
            info = {}
            for line in open(self._filename):
                if line.startswith("%package "):
                    if packages:
                        for pkg in packages:
                            self._details[pkg] = info
                    packages = line[(9):].rstrip("\n").split(" ")
                    in_pre = in_description = False
                    info = {}
                elif not (in_pre or in_description):
                    if line.startswith("Update: "):
                        info["update"] = line[8:].rstrip("\n")
                    if line.startswith("Importance: "):
                        info["importance"] = line[12:].rstrip("\n")
                        for pkg in packages:
                            flagdict[pkg] = info["importance"]
                    if line.startswith("ID: "):
                        info["id"] = line[4:].rstrip("\n")
                    if line.startswith("URL: "):
                        info["url"] = line[5:].rstrip("\n")
                if in_description:
                    if "description" in info:
                        info["description"] += line
                    else:
                        info["description"] = line
                if line.startswith("%description"):
                    in_description = True
                    in_pre = False
                if in_pre:
                    if "pre" in info:
                        info["pre"] += line
                    else:
                        info["pre"] = line
                if line.startswith("%pre"):
                    in_pre = True
                    in_description = False
            if packages:
                for pkg in packages:
                    self._details[pkg] = info
            self._flagdict = flagdict
        except (IOError):
            pass
        
    def getErrataFlags(self):
        return self._flagdict

    def setErrataFlags(self):
        # Can't set flags when in read-only mode
        if sysconf.getReadOnly():
            return

        for pkg, type in self._flagdict.iteritems():
            pkgconf.setFlag(type, pkg)

    def getType(self, package):
        return self._flagdict.get(package.name, None)

    def getInfo(self, package):
        return self._details.get(package.name, None)


# vim:ts=4:sw=4:et

#
# Copyright (c) 2008 afb datakonsult
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
from smart.cache import Loader, PackageInfo
from smart.backends.deb.base import *
from smart import *
import os
import sys
import string

# Package: macosx
# Status: install ok installed
# Version: 10.4.11-1
# homepage: http://www.finkproject.org/faq/usage-general.php#virtpackage
# description: [virtual package representing the system]
#

class FinkVirtualPkgInfo(PackageInfo):

    def __init__(self, package, info):
        PackageInfo.__init__(self, package)
        self._info = info

    def getGroup(self):
        return "virtual"

    def getSummary(self):
        return self._info.get("description", "")

    def getDescription(self):
        return ""

    def getReferenceURLs(self):
        return [self._info.get("homepage", "")]

    def getURLs(self):
        return [] # not real package

    def getPathList(self):
        return [] # no real file list

class FinkVirtualPkgsLoader(Loader):

    def _parseOutput(self, lines):
        """
        Split virtual package information out per pkg.
        """
    
        pkgs = []
        info = {}
        for line in lines:
            line = string.rstrip(line)
            keyval = string.split(line, ':', 1)
            if len(keyval) > 1:
               val = string.lstrip(keyval[1])
               info[keyval[0]] = val
            else:
                pkgs.append(info)
                info = {}
        return pkgs

    def __init__(self, path):
        Loader.__init__(self)
        self._path = path
        self._baseurl = None

    def getInfoList(self):
        return []

    def load(self):

        prog = iface.getProgress(self._cache)

        output = os.popen(self._path).readlines()
        pkgs = self._parseOutput(output)

        for info in pkgs:

            name = info["Package"]
            version = info["Version"]

            prvargs = reqargs = upgargs = cnfargs = []

            prvargs = [(DebNameProvides, name, version)]
            provides = string.split(info.get("provides",""), ', ')
            for provide in provides:
               prvargs.append((DebNameProvides, provide, None))

            pkg = self.buildPackage((DebPackage, name, version),
                                    prvargs, reqargs, upgargs, cnfargs)
            pkg.loaders[self] = info

            status = info.get("Status")
            if status.find("installed") != -1:
                pkg.installed = True
            if status.find("not-installed") != -1:
                pkg.installed = False

            prog.add(1)
            prog.show()

    def getInfo(self, pkg):
        return FinkVirtualPkgInfo(pkg, pkg.loaders[self])



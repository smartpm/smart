#
# Copyright (c) 2004-2005 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#            Michael Scherer <misc@mandrake.org>
#
# Adapted from slack/loader.py and metadata.py by Michael Scherer.
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
from smart.cache import PackageInfo, Loader
from smart.backends.rpm.base import *
from smart import *
import posixpath
import os
import re

DEPENDSRE = re.compile("^([^[]*)(?:\[\*\])*(\[.*])?")
OPERATIONRE = re.compile("\[([<>=]*) *(.*)\]")


class URPMISynthesisPackageInfo(PackageInfo):
    def __init__(self, package, loader, info):
        PackageInfo.__init__(self, package)
        self._loader = loader
        self._info = info

    def getURLs(self):
        rpmname = "%s-%s.%s.rpm" % (self._info["name"],
                                    self._info["version"],
                                    self._info["arch"])
        return [posixpath.join(self._loader._baseurl, rpmname)]

    def getInstalledSize(self):
        return int(self._info.get("size"))

    def getSummary(self):
        return self._info.get("summary", "")

    def getGroup(self):
        return self._info.get("group", "")


class URPMISynthesisLoader(Loader):

    __stateversion__ = Loader.__stateversion__+1

    def __init__(self, filename, baseurl, filelistname):
        Loader.__init__(self)
        self._filename = filename
        self._baseurl = baseurl
        self._filelistname = filelistname

    def getInfo(self, pkg):
        return URPMISynthesisPackageInfo(pkg, self, pkg.loaders[self])
	
    def getLoadSteps(self):
        indexfile = open(self._filename)
        total = 0
        for line in indexfile:
            if line.startswith("@info@"):
                total += 1
        indexfile.close()
        return total
    
    def splitDepends(self, depsarray, _dependsre=DEPENDSRE,
                     _operationre=OPERATIONRE):
        result = []
        for deps in depsarray:
            depends = _dependsre.match(deps)
            if depends:
                name = depends.groups()[0]
                operation = ""
                version = ""
                condition = depends.groups()[1]
                if condition:
                    o = _operationre.match(condition)
                    if o:
                        (operation, version) = o.groups()[0:2]
                        
                        if operation == "==": operation = "="
                result.append((name, operation, version))
        return result

    def load(self):

        requires = ()
        provides = ()
        conflicts = ()
        obsoletes = ()

        prog = iface.getProgress(self._cache)

        for line in open(self._filename):

            element = line[1:-1].split("@")
            id = element.pop(0)

            if id == "summary":
                summary = element[0]

            elif id == "provides":
                provides = self.splitDepends(element)

            elif id == "requires":
                requires = self.splitDepends(element)

            elif id == "conflicts":
                conflicts = self.splitDepends(element)

            elif id == "obsoletes":
                obsoletes = self.splitDepends(element)

            elif id == "info":

                rpmnameparts = element[0].split("-")
                version = "-".join(rpmnameparts[-2:])
                # Replace . by @
                versionarch = "@".join(version.rsplit(".", 1))
                version, arch = versionarch.split("@", 1)[0:2]

                if element[1] != "0":
                    version = "%s:%s" % (element[1], version)
                name = "-".join(rpmnameparts[0:-2])

                info = {}
                info["version"] = version
                info["name"] = name
                info["arch"] = arch
                info["summary"] = summary
                info["size"] = element[2]
                info["group"] = element[3]

                prvdict = {}
                for i in provides:
                    prv = (RPMProvides, i[0], i[2])
                    prvdict[prv] = True

                reqdict = {}
                for i in requires:
                    req = (RPMRequires, i[0], i[1], i[2])
                    reqdict[req] = True

                cnfdict = {}
                for i in conflicts:
                    cnf = (RPMConflicts, i[0], i[1], i[2])
                    cnfdict[cnf] = True

                upgdict = {}
                upgdict[(RPMObsoletes, name, "<", version)] = True

                for i in obsoletes:
                    upg = (RPMObsoletes, i[0], i[1], i[2])
                    upgdict[upg] = True
                    cnfdict[upg] = True
                    
                pkg = self.buildPackage((RPMPackage, name, versionarch),
                                        prvdict.keys(), reqdict.keys(),
                                        upgdict.keys(), cnfdict.keys())
                pkg.loaders[self] = info

                prog.add(1)
                prog.show()

                provides = ()
                requires = ()
                conflicts = ()
                obsoletes = ()

# vim:ts=4:sw=4:et

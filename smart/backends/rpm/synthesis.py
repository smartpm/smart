# -*- coding: utf-8 -*-
#
# Copyright (c) 2004-2005 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#            Michael Scherer <misc@mandrake.org>
#            Per Øyvind Karlsen <peroyvind@mandriva.org>
#
# Adapted from slack/loader.py and metadata.py by Michael Scherer.
# Support for xml metadata format by Per Øyvind Karlsen.
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
from smart.backends.rpm.rpmver import splitarch, checkver
from smart.cache import PackageInfo, Loader
from smart.backends.rpm.base import *
try:
    from xml.etree import cElementTree        
except ImportError:
    try:
        import cElementTree
    except ImportError:     
        from smart.util import cElementTree

from smart import *
import posixpath
import os
import re

from xml.parsers import expat

DEPENDSRE = re.compile("^([^[]*)(\[\*\])?(\[.*\])?")
OPERATIONRE = re.compile("\[([<>=]*) *(.+)?\]")
EPOCHRE = re.compile("[0-9]+:")


class URPMISynthesisPackageInfo(PackageInfo):
    def __init__(self, package, loader, info):
        PackageInfo.__init__(self, package)
        self._loader = loader
        self._info = info

    def getURLs(self):
        return [posixpath.join(self._loader._baseurl,
                               self._loader.getFileName(self))]

    def getSize(self, url):
        return self._info.get("filesize")

    def getInstalledSize(self):
        return int(self._info.get("size"))

    def getSummary(self):
        return self._info.get("summary", "")

    def getGroup(self):
        return self._info.get("group", "")

    def getDescription(self):
        return self._info.get("description")

    def getReferenceURLs(self):
        return [self._info.get("url", "")]

    def getSource(self):
        sourcerpm = self._info.get("sourcerpm", "")
        sourcerpm = sourcerpm.replace(".src", "")
        sourcerpm = sourcerpm.replace(".nosrc", "")
        return sourcerpm.replace(".rpm", "")
    
    def getLicense(self):
        return self._info.get("license", "")

class URPMISynthesisLoader(Loader):

    __stateversion__ = Loader.__stateversion__+3

    def __init__(self, filename, baseurl, listfile, infofile=None):
        Loader.__init__(self)
        self._filename = filename
        self._baseurl = baseurl
        self._prefix = {}
        self._infofile = infofile
        self._flagdict = None

    def setErrataFlags(self, flagdict):
        self._flagdict = flagdict
    
    def buildPackage(self, pkgargs, prvargs, reqargs, upgargs, cnfargs):
        pkg = Loader.buildPackage(self, pkgargs, prvargs, reqargs, upgargs, cnfargs)
        name = pkgargs[1]
        if hasattr(self, '_flagdict') and self._flagdict and name in self._flagdict:
            if not sysconf.getReadOnly():
                pkgconf.setFlag(self._flagdict[name], name, "=", pkgargs[2])
        return pkg

    def getInfo(self, pkg):
        return URPMISynthesisPackageInfo(pkg, self, pkg.loaders[self])

    def getFileName(self, info):
        if "nvra" in info._info:
            filename = "%s.rpm" % info._info.get("nvra")
        else:
            name = info._package.name
            version, arch = splitarch(info._package.version)
            version = EPOCHRE.sub("", version)
            filename = "%s-%s.%s.rpm" % (name, version, arch)
        if filename in self._prefix:
            filename = os.path.join(self._prefix[filename], filename)
        return filename
	
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
                name, flag, condition = depends.groups()
                operation = None
                version = None
                if condition:
                    o = _operationre.match(condition)
                    if o:
                        operation, version = o.groups()
                        if operation == "==":
                            operation = "="
                        if version and version.startswith("0:"):
                            version = version[2:]
                result.append((name, operation, version, bool(flag)))
        return result

    def load(self):

        Pkg = RPMPackage
        Prv = RPMProvides
        NPrv = RPMNameProvides
        PreReq = RPMPreRequires
        Req = RPMRequires
        Obs = RPMObsoletes
        Cnf = RPMConflicts

        summary = None
        filesize = None
        
        requires = ()
        provides = ()
        conflicts = ()
        obsoletes = ()

        prog = iface.getProgress(self._cache)

        if self._infofile:
            try:
                infofile = self._infofile
                # mandriva version didn't uncompress
                if infofile.endswith(".lzma"):
                    import lzma
                    infofile = lzma.LZMAFile(infofile)
                infoxml = cElementTree.parse(infofile).getroot()
            except (expat.error, SyntaxError), e: # ElementTree.ParseError
                raise Error, _("Invalid XML file:\n  %s\n  %s") % \
                              (self._infofile, str(e))
        else:
            infoxml = None

        for line in open(self._filename):

            element = line[1:-1].split("@")
            id = element.pop(0)

            if id == "summary":
                summary = element[0]

            elif id == "filesize":
                filesize = int(element[0])

            elif id == "provides":
                provides = self.splitDepends(element)

            elif id == "requires":
                requires = self.splitDepends(element)

            elif id == "conflicts":
                conflicts = self.splitDepends(element)

            elif id == "obsoletes":
                obsoletes = self.splitDepends(element)

            elif id == "info":

                description = ""
                sourcerpm = ""
                url = ""            
                license = ""

                if infoxml:
                    infoelement = infoxml[0]

                    # info.xml should have the same order as synthesis, but if
                    # they're not in sync, we try find the matching package
                    if infoelement.get("fn") != element[0]:
                        for elem in infoxml:
                            if elem.get("fn") == element[0]:
                                infoelement = elem
                                break
                    # Let's check again to be really sure that we have the
                    # correct package
                    if infoelement.get("fn") == element[0]:
                        description = infoelement.text.strip()
                        sourcerpm = infoelement.get("sourcerpm")
                        url = infoelement.get("url")
                        license = infoelement.get("license")
                        infoxml.remove(infoelement)

                rpmnameparts = element[0].split("-")

                disttag = None
                distepoch = None
                releasepos = -2
                for provide in provides:
                    if provide[2]:
                        first = provide[2].split("-")
                        if len(first) > 1:
                            second = first[1].split(":")
                            if len(second) > 1:
                                distepoch = second[1]
                                disttag = rpmnameparts[-1].split(distepoch)[0]
                                releasepos -= 1
                                break

                version = "-".join(rpmnameparts[releasepos:])
                epoch = element[1]
                if epoch != "0":
                    version = "%s:%s" % (epoch, version)

                dot = version.rfind(".")
                if dot == -1:
                    arch = "unknown"
                else:
                    version, arch = version[:dot], version[dot+1:]
                if disttag and distepoch:
                    version = version.replace("-%s%s" % (disttag, distepoch), "")              
                versionarch = "%s@%s" % (version, arch)
                
                if getArchScore(arch) == 0:
                    continue

                name = "-".join(rpmnameparts[0:releasepos])

                info = {"nvra": element[0],
                        "summary": summary,
                        "filesize": filesize,
                        "size"   : element[2],
                        "group"  : element[3],
                        "description" : description,
                        "sourcerpm" : sourcerpm,
                        "url"    : url,
                        "license": license}

                prvdict = {}
                for n, r, v, f in provides:
                    if n == name and checkver(v, version):
                        prv = (NPrv, n, versionarch)
                    else:
                        prv = (Prv, n, v)
                    prvdict[prv] = True

                reqdict = {}
                for n, r, v, f in requires:
                    if not ((r is None or "=" in r) and
                            (Prv, n, v) in prvdict or
                            system_provides.match(n, r, v)):
                        if f:
                            reqdict[(PreReq, n, r, v)] = True
                        else:
                            reqdict[(Req, n, r, v)] = True

                cnfdict = {}
                for n, r, v, f in conflicts:
                    cnfdict[(Cnf, n, r, v)] = True

                upgdict = {}
                upgdict[(Obs, name, "<", versionarch)] = True

                for n, r, v, f in obsoletes:
                    upg = (Obs, n, r, v)
                    upgdict[upg] = True
                    cnfdict[upg] = True
                    
                if disttag:
                    distversion = "%s-%s" % (version, disttag)
                    if distepoch:
                        distversion += distepoch
                    versionarch = "%s@%s" % (distversion, arch)
                pkg = self.buildPackage((Pkg, name, versionarch),
                                        prvdict.keys(), collapse_libc_requires(reqdict.keys()),
                                        upgdict.keys(), cnfdict.keys())
                pkg.loaders[self] = info

                prog.add(1)
                prog.show()

                summary = None
                filesize = None
                
                provides = ()
                requires = ()
                conflicts = ()
                obsoletes = ()

def enablePsyco(psyco):
    psyco.bind(URPMISynthesisLoader.getLoadSteps)
    psyco.bind(URPMISynthesisLoader.splitDepends)
    psyco.bind(URPMISynthesisLoader.load)

hooks.register("enable-psyco", enablePsyco)

# vim:ts=4:sw=4:et

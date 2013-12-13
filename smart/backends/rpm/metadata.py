#
# Copyright (c) 2005 Canonical
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
from smart.backends.rpm.rpmver import checkver
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
import locale
import os

NS_COMMON    = "http://linux.duke.edu/metadata/common"
NS_RPM       = "http://linux.duke.edu/metadata/rpm"
NS_FILELISTS = "http://linux.duke.edu/metadata/filelists"

BYTESPERPKG = 3000

def nstag(ns, tag):
    return "{%s}%s" % (ns, tag)

class RPMMetaDataPackageInfo(PackageInfo):

    def __init__(self, package, loader, info):
        PackageInfo.__init__(self, package)
        self._loader = loader
        self._info = info

    def getURLs(self):
        url = self._info.get("location")
        if url:
            return [posixpath.join(self._loader._baseurl, url)]
        return []

    def getBuildTime(self):
        return self._info.get("build_time")

    def getInstalledSize(self):
        return self._info.get("installed_size")

    def getSize(self, url):
        return self._info.get("size")

    def getMD5(self, url):
        return self._info.get("md5")

    def getSHA(self, url):
        return self._info.get("sha")

    def getSHA256(self, url):
        return self._info.get("sha256")

    def getDescription(self):
        return self._info.get("description", "")

    def getSummary(self):
        return self._info.get("summary", "")

    def getReferenceURLs(self):
        return [self._info.get("url", "")]

    def getSource(self):
        sourcerpm = self._info.get("sourcerpm", "")
        sourcerpm = sourcerpm.replace(".src", "")
        sourcerpm = sourcerpm.replace(".nosrc", "")
        return sourcerpm.replace(".rpm", "")
    
    def getGroup(self):
        return self._info.get("group", "")

    def getLicense(self):
        return self._info.get("license", "")


class RPMMetaDataLoader(Loader):

    __stateversion__ = Loader.__stateversion__+3
 
    def __init__(self, filename, filelistsname, baseurl):
        Loader.__init__(self)
        self._filename = filename
        self._filelistsname = filelistsname
        self._baseurl = baseurl
        self._fileprovides = {}
        self._parsedflist = False
        self._pkgids = {}

    def reset(self):
        Loader.reset(self)
        self._fileprovides.clear()
        self._parsedflist = False
        self._pkgids.clear()

    def getInfo(self, pkg):
        return RPMMetaDataPackageInfo(pkg, self, pkg.loaders[self])

    def getLoadSteps(self):
        return os.path.getsize(self._filename)/BYTESPERPKG

    def load(self):
        METADATA    = nstag(NS_COMMON, "metadata")
        PACKAGE     = nstag(NS_COMMON, "package")
        NAME        = nstag(NS_COMMON, "name")
        ARCH        = nstag(NS_COMMON, "arch")
        VERSION     = nstag(NS_COMMON, "version")
        SUMMARY     = nstag(NS_COMMON, "summary")
        DESCRIPTION = nstag(NS_COMMON, "description")
        URL         = nstag(NS_COMMON, "url")
        TIME        = nstag(NS_COMMON, "time")
        SIZE        = nstag(NS_COMMON, "size")
        LOCATION    = nstag(NS_COMMON, "location")
        FORMAT      = nstag(NS_COMMON, "format")
        CHECKSUM    = nstag(NS_COMMON, "checksum")
        FILE        = nstag(NS_COMMON, "file")
        SOURCERPM   = nstag(NS_RPM, "sourcerpm")
        GROUP       = nstag(NS_RPM, "group")
        LICENSE     = nstag(NS_RPM, "license")
        ENTRY       = nstag(NS_RPM, "entry")
        REQUIRES    = nstag(NS_RPM, "requires")
        PROVIDES    = nstag(NS_RPM, "provides")
        CONFLICTS   = nstag(NS_RPM, "conflicts")
        OBSOLETES   = nstag(NS_RPM, "obsoletes")
        DISTTAG     = nstag(NS_RPM, "disttag")
        DISTEPOCH   = nstag(NS_RPM, "distepoch")

        COMPMAP = { "EQ":"=", "LT":"<", "LE":"<=", "GT":">", "GE":">="}

        # Prepare progress reporting.
        lastoffset = 0
        mod = 0
        progress = iface.getProgress(self._cache)

        # Prepare package information.
        name = None
        version = None
        arch = None
        disttag = None
        distepoch = None
        info = {}
        reqdict = {}
        recdict = {}
        prvdict = {}
        upgdict = {}
        cnfdict = {}
        filedict = {}

        # Prepare data useful for the iteration
        skip = None
        queue = []

        file = open(self._filename)
        for event, elem in cElementTree.iterparse(file, ("start", "end")):
            tag = elem.tag

            if event == "start":

                if not skip and tag == PACKAGE:
                    if elem.get("type") != "rpm":
                        skip = PACKAGE

                queue.append(elem)

            elif event == "end":

                popped = queue.pop()
                assert popped is elem

                if skip:
                    if tag == skip:
                        skip = None

                elif tag == ARCH:
                    if getArchScore(elem.text) == 0:
                        skip = PACKAGE
                    else:
                        arch = elem.text

                elif tag == NAME:
                    name = elem.text

                elif tag == VERSION:
                    e = elem.get("epoch")
                    if e and e != "0":
                        version = "%s:%s-%s" % \
                                  (e, elem.get("ver"), elem.get("rel"))
                    else:
                        version = "%s-%s" % \
                                  (elem.get("ver"), elem.get("rel"))

                elif tag == DISTTAG:
                    disttag = elem.text

                elif tag == DISTEPOCH:
                    distepoch = elem.text

                elif tag == SUMMARY:
                    if elem.text:
                        info["summary"] = elem.text

                elif tag == DESCRIPTION:
                    if elem.text:
                        info["description"] = elem.text

                elif tag == URL:
                    if elem.text:
                        info["url"] = elem.text

                elif tag == TIME:
                    info["time"] = int(elem.get("file"))
                    info["build_time"] = int(elem.get("build"))

                elif tag == SIZE:
                    info["size"] = int(elem.get("package"))
                    if elem.get("installed"):
                        info["installed_size"] = int(elem.get("installed"))

                elif tag == CHECKSUM:
                    info[elem.get("type")] = elem.text
                    if elem.get("pkgid") == "YES":
                        pkgid = elem.text

                elif tag == LOCATION:
                    info["location"] = elem.get("href")

                elif tag == SOURCERPM:
                    if elem.text:
                        info["sourcerpm"] = elem.text

                elif tag == GROUP:
                    if elem.text:
                        info["group"] = elem.text

                elif tag == LICENSE:
                    if elem.text:
                        info["license"] = elem.text

                elif tag == FILE:
                    filedict[elem.text] = True

                elif tag == ENTRY:
                    ename = elem.get("name")
                    if (not ename or
                        ename[:7] in ("rpmlib(", "config(")):
                        continue

                    if "ver" in elem.keys():
                        e = elem.get("epoch")
                        v = elem.get("ver")
                        r = elem.get("rel")
                        eversion = v
                        if e and e != "0":
                            eversion = "%s:%s" % (e, eversion)
                        if r:
                            eversion = "%s-%s" % (eversion, r)
                        if "flags" in elem.keys():
                            erelation = COMPMAP.get(elem.get("flags"))
                        else:
                            erelation = None
                    else:
                        eversion = None
                        erelation = None

                    lasttag = queue[-1].tag
                    if lasttag == REQUIRES:
                        if elem.get("missingok") == "1":
                            recdict[(RPMRequires,
                                    ename, erelation, eversion)] = True
                        else:
                            if elem.get("pre") == "1":
                                reqdict[(RPMPreRequires,
                                        ename, erelation, eversion)] = True
                            else:
                                reqdict[(RPMRequires,
                                        ename, erelation, eversion)] = True

                    elif lasttag == PROVIDES:
                        if ename[0] == "/":
                            filedict[ename] = True
                        else:
                            if ename == name and checkver(eversion, version):
                                eversion = "%s@%s" % (eversion, arch)
                                Prv = RPMNameProvides
                            else:
                                Prv = RPMProvides
                            prvdict[(Prv, ename.encode('utf-8'), eversion)] = True

                    elif lasttag == OBSOLETES:
                        tup = (RPMObsoletes, ename, erelation, eversion)
                        upgdict[tup] = True
                        cnfdict[tup] = True

                    elif lasttag == CONFLICTS:
                        cnfdict[(RPMConflicts,
                                 ename, erelation, eversion)] = True
                                    
                elif elem.tag == PACKAGE:

                    # Use all the information acquired to build the package.

                    versionarch = "%s@%s" % (version, arch)

                    upgdict[(RPMObsoletes,
                             name, '<', versionarch)] = True

                    reqargs = [x for x in reqdict
                               if not ((x[2] is None or "=" in x[2]) and
                                       (RPMProvides, x[1], x[3]) in prvdict or
                                       system_provides.match(x[1], x[2], x[3]))]
                    reqargs = collapse_libc_requires(reqargs)

                    recargs = [x for x in recdict
                               if not ((x[2] is None or "=" in x[2]) and
                                       (RPMProvides, x[1], x[3]) in prvdict or
                                       system_provides.match(x[1], x[2], x[3]))]

                    prvargs = prvdict.keys()
                    cnfargs = cnfdict.keys()
                    upgargs = upgdict.keys()

                    if disttag:
                        distversion = "%s-%s" % (version, disttag)
                        if distepoch:
                            distversion += distepoch
                        versionarch = "%s@%s" % (distversion, arch)

                    pkg = self.buildPackage((RPMPackage, name, versionarch),
                                            prvargs, reqargs, upgargs, cnfargs, recargs)
                    pkg.loaders[self] = info

                    # Store the provided files for future usage.
                    if filedict:
                        for filename in filedict:
                            lst = self._fileprovides.get(filename)
                            if not lst:
                                self._fileprovides[filename] = [pkg]
                            else:
                                lst.append(pkg)

                    if pkgid:
                        self._pkgids[pkgid] = pkg

                    # Reset all information.
                    name = None
                    version = None
                    arch = None
                    disttag = None
                    distepoch = None
                    pkgid = None
                    reqdict.clear()
                    recdict.clear()
                    prvdict.clear()
                    upgdict.clear()
                    cnfdict.clear()
                    filedict.clear()
                    # Do not clear it. pkg.loaders has a reference.
                    info = {}

                    # Update progress
                    offset = file.tell()
                    div, mod = divmod(offset-lastoffset+mod, BYTESPERPKG)
                    lastoffset = offset
                    progress.add(div)
                    progress.show()

                elem.clear()

        file.close()

    def loadFileProvides(self, fndict):
        bfp = self.buildFileProvides
        parsed = self._parsedflist
        for fn in fndict:
            if fn not in self._fileprovides:
                if not parsed:
                    self._parsedflist = parsed = True
                    self.parseFilesList(fndict)
                    if fn not in self._fileprovides:
                        pkgs = self._fileprovides[fn] = ()
                    else:
                        pkgs = self._fileprovides[fn]
                else:
                    pkgs = self._fileprovides[fn] = ()
            else:
                pkgs = self._fileprovides[fn]

            if pkgs:
                for pkg in pkgs:
                    bfp(pkg, (RPMProvides, fn, None))


    def parseFilesList(self, fndict):
        FILE    = nstag(NS_FILELISTS, "file")
        PACKAGE = nstag(NS_FILELISTS, "package")

        pkgids = self._pkgids
        fileprovides = self._fileprovides

        pkg = None
        skip = None
        file = open(self._filelistsname)
        for event, elem in cElementTree.iterparse(file, ("start", "end")):
            if event == "start":
                if not skip and elem.tag == PACKAGE:
                    if elem.get("arch") == "src":
                        skip = PACKAGE
                    else:
                        pkg = pkgids.get(elem.get("pkgid"))
                        if not pkg:
                            skip = PACKAGE
            elif event == "end":
                if skip:
                    if elem.tag == skip:
                        skip = None
                elif elem.tag == FILE and elem.text in fndict:
                    pkgs = fileprovides.get(elem.text)
                    if not pkgs:
                        fileprovides[elem.text] = [pkg]
                    else:
                        pkgs.append(pkg)
                elem.clear()
        file.close()

def enablePsyco(psyco):
    psyco.bind(RPMMetaDataLoader.load)
    psyco.bind(RPMMetaDataLoader.loadFileProvides)
    psyco.bind(RPMMetaDataLoader.parseFilesList)

hooks.register("enable-psyco", enablePsyco)

# vim:ts=4:sw=4:et

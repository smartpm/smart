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
from gepeto.cache import Loader, PackageInfo
from gepeto.backends.deb.debver import parseversion
from gepeto.backends.deb.tagfile import TagFile
from gepeto.backends.deb import *
from gepeto import *
import locale
import stat
import os

ENCODING = locale.getpreferredencoding()

class DebPackageInfo(PackageInfo):

    class LazyDict(object):
        def __get__(self, obj, type):
            obj._dict = obj._loader.getDict(obj._package)
            return obj._dict

    _dict = LazyDict()

    def __init__(self, package, loader):
        PackageInfo.__init__(self, package)
        self._loader = loader

    def getURLs(self):
        url = self._loader.getURL()
        if url and "filename" in self._dict:
            return [os.path.join(url, self._dict["filename"])]
        return []

    def getSize(self, url):
        size = self._dict.get("size")
        if size:
            return long(size)
        return None

    def getMD5(self, url):
        return self._dict.get("md5sum")

    def getInstalledSize(self):
        size = self._dict.get("installed-size")
        if size:
            return long(size)*1024
        return None

    def getDescription(self):
        toks = self._dict.get("description").split("\n", 1)
        if len(toks) == 2:
            return toks[1]
        return ""

    def getSummary(self):
        description = self._dict.get("description")
        if description:
            return description.split("\n", 1)[0]
        return ""

    def getGroup(self):
        return self._package._section

class DebTagFileLoader(Loader):

    def __init__(self, filename, baseurl=None):
        Loader.__init__(self)
        self._filename = filename
        self._baseurl = baseurl
        self._tagfile = TagFile(self._filename)

    def getLoadSteps(self):
        return os.path.getsize(self._filename)/800

    def getSections(self, prog):
        tf = self._tagfile
        tf.setOffset(0)
        lastoffset = offset = mod = 0
        while tf.advanceSection():
            yield tf, offset
            offset = tf.getOffset()
            div, mod = divmod(offset-lastoffset+mod, 800)
            prog.add(div)
            prog.show()
            lastoffset = offset

    def getInfo(self, pkg):
        return DebPackageInfo(pkg, self)

    def getDict(self, pkg):
        self._tagfile.setOffset(pkg.loaders[self])
        self._tagfile.advanceSection()
        return self._tagfile.copy()

    def getURL(self):
        return self._baseurl

    def reset(self):
        Loader.reset(self)
        self._offsets = {}

    def load(self):
        Pkg = DebPackage
        Prv = DebProvides
        NPrv = DebNameProvides
        PreReq = DebPreRequires
        Req = DebRequires
        OrReq = DebOrRequires
        OrPreReq = DebOrPreRequires
        Upg = DebUpgrades
        Cnf = DebConflicts
        prog = iface.getProgress(self._cache)
        for section, offset in self.getSections(prog):
            name = section.get("package")
            version = section.get("version")

            prvargs = [(NPrv, name, version)]
            value = section.get("provides")
            if value:
                for prvname in value.split(","):
                    prvargs.append((Prv, prvname.strip()))

            reqargs = []
            value = section.get("depends")
            if value:
                for descr in value.split(","):
                    opts = descr.split("|")
                    if len(opts) == 1:
                        n, r, v = parseversion(opts[0])
                        reqargs.append((Req, n, r, v))
                    else:
                        nrv = []
                        for subdescr in opts:
                            nrv.append(parseversion(subdescr))
                        reqargs.append((OrReq, tuple(nrv), descr))
            value = section.get("pre-depends")
            if value:
                for descr in value.split(","):
                    opts = descr.split("|")
                    if len(opts) == 1:
                        n, r, v = parseversion(opts[0])
                        reqargs.append((PreReq, n, r, v))
                    else:
                        nrv = []
                        for subdescr in opts:
                            nrv.append(parseversion(subdescr))
                        reqargs.append((OrPreReq, tuple(nrv), descr))

            upgargs = [(Upg, name, '<', version)]

            cnfargs = []
            value = section.get("conflicts")
            if value:
                for descr in value.split(","):
                    n, r, v = parseversion(descr)
                    cnfargs.append((Cnf, n, r, v))

            pkg = self.buildPackage((Pkg, name, version),
                                    prvargs, reqargs, upgargs, cnfargs)
            pkg.loaders[self] = offset
            pkg._section = section.get("section", "")
            self._offsets[offset] = pkg

# vim:ts=4:sw=4:et

#
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
#from smart.backends.rpm.rpmver import splitarch
from smart.backends.rpm.crpmver import splitarch
from smart.cache import Loader, PackageInfo
from smart.channel import FileChannel
from smart.backends.rpm import *
from smart import *
import locale
import stat
import rpm
import os

CRPMTAG_FILENAME          = 1000000
CRPMTAG_FILESIZE          = 1000001
CRPMTAG_MD5               = 1000005
CRPMTAG_SHA1              = 1000006

CRPMTAG_DIRECTORY         = 1000010
CRPMTAG_BINARY            = 1000011

CRPMTAG_UPDATE_SUMMARY    = 1000020
CRPMTAG_UPDATE_IMPORTANCE = 1000021
CRPMTAG_UPDATE_DATE       = 1000022
CRPMTAG_UPDATE_URL        = 1000023

ENCODING = locale.getpreferredencoding()

class RPMHeaderPackageInfo(PackageInfo):

    class LazyHeader(object):
        def __get__(self, obj, type):
            obj._h = obj._loader.getHeader(obj._package)
            return obj._h

    _h = LazyHeader()

    def __init__(self, package, loader):
        PackageInfo.__init__(self, package)
        self._loader = loader
        self._path = None

    def getURLs(self):
        url = self._loader.getURL()
        if url:
            return [os.path.join(url, self._loader.getFileName(self))]
        return []

    def getSize(self, url):
        return self._loader.getSize(self)

    def getMD5(self, url):
        return self._loader.getMD5(self)

    def getInstalledSize(self):
        return self._h[rpm.RPMTAG_SIZE]

    def getDescription(self):
        return self._h[rpm.RPMTAG_DESCRIPTION].decode(ENCODING)

    def getSummary(self):
        return self._h[rpm.RPMTAG_SUMMARY].decode(ENCODING)

    def getGroup(self):
        return self._package._group.decode(ENCODING)

    def getPathList(self):
        if self._path is None:
            paths = self._h[rpm.RPMTAG_OLDFILENAMES]
            modes = self._h[rpm.RPMTAG_FILEMODES]
            if modes:
                self._path = {}
                for i in range(len(paths)):
                    self._path[paths[i]] = modes[i]
            else:
                self._path = dict.fromkeys(paths, 0)
        return self._path.keys()

    def pathIsDir(self, path):
        return stat.S_ISDIR(self._path[path])

    def pathIsLink(self, path):
        return stat.S_ISLNK(self._path[path])

    def pathIsFile(self, path):
        return stat.S_ISREG(self._path[path])

    def pathIsSpecial(self, path):
        mode = self._path[path]
        return not (stat.S_ISDIR(mode) or
                    stat.S_ISLNK(mode) or
                    stat.S_ISREG(mode))

class RPMHeaderLoader(Loader):
 
    COMPFLAGS = rpm.RPMSENSE_EQUAL|rpm.RPMSENSE_GREATER|rpm.RPMSENSE_LESS

    COMPMAP = { rpm.RPMSENSE_EQUAL:   "=",
                rpm.RPMSENSE_LESS:    "<",
                rpm.RPMSENSE_GREATER: ">",
                rpm.RPMSENSE_EQUAL|rpm.RPMSENSE_LESS:    "<=",
                rpm.RPMSENSE_EQUAL|rpm.RPMSENSE_GREATER: ">=" }

    def __init__(self):
        Loader.__init__(self)
        self._offsets = {}

    def getHeaders(self, prog):
        return []

    def getInfo(self, pkg):
        return RPMHeaderPackageInfo(pkg, self)

    def reset(self):
        Loader.reset(self)
        self._offsets.clear()

    def load(self):
        CM = self.COMPMAP
        CF = self.COMPFLAGS
        Pkg = RPMPackage
        Prv = RPMProvides
        NPrv = RPMNameProvides
        PreReq = RPMPreRequires
        Req = RPMRequires
        Obs = RPMObsoletes
        Cnf = RPMConflicts
        prog = iface.getProgress(self._cache)
        for h, offset in self.getHeaders(prog):
            arch = h[1022] # RPMTAG_ARCH
            if rpm.archscore(arch) == 0:
                continue

            name = h[1000] # RPMTAG_NAME
            epoch = h[1003] # RPMTAG_EPOCH
            if epoch is not None:
                # RPMTAG_VERSION, RPMTAG_RELEASE
                version = "%s:%s-%s" % (epoch, h[1001], h[1002])
            else:
                # RPMTAG_VERSION, RPMTAG_RELEASE
                version = "%s-%s" % (h[1001], h[1002])
            versionarch = "%s.%s" % (version, arch)

            n = h[1047] # RPMTAG_PROVIDENAME
            v = h[1113] # RPMTAG_PROVIDEVERSION
            prvdict = {}
            for i in range(len(n)):
                ni = n[i]
                if not ni.startswith("config("):
                    vi = v[i]
                    if ni == name and vi == version:
                        prvdict[(NPrv, ni, versionarch)] = True
                    else:
                        prvdict[(Prv, ni, vi or None)] = True
            prvargs = prvdict.keys()

            n = h[1049] # RPMTAG_REQUIRENAME
            if n:
                f = h[1048] # RPMTAG_REQUIREFLAGS
                v = h[1050] # RPMTAG_REQUIREVERSION
                reqdict = {}
                for i in range(len(n)):
                    ni = n[i]
                    if ni[:7] not in ("rpmlib(", "config("):
                        vi = v[i] or None
                        r = CM.get(f[i]&CF)
                        if ((r is not None and r != "=") or
                            ((Prv, ni, vi) not in prvdict)):
                            # RPMSENSE_PREREQ
                            reqdict[(f[i]&64 and PreReq or Req,
                                     ni, r, vi)] = True
                reqargs = reqdict.keys()
            else:
                reqargs = None

            n = h[1054] # RPMTAG_CONFLICTNAME
            if n:
                f = h[1053] # RPMTAG_CONFLICTFLAGS
                v = h[1055] # RPMTAG_CONFLICTVERSION
                cnfargs = [(Cnf, n[i], CM.get(f[i]&CF), v[i] or None)
                           for i in range(len(n))]
            else:
                cnfargs = []

            obstup = (Obs, name, '<', versionarch)

            n = h[1090] # RPMTAG_OBSOLETENAME
            if n:
                f = h[1114] # RPMTAG_OBSOLETEFLAGS
                v = h[1115] # RPMTAG_OBSOLETEVERSION
                upgargs = [(Obs, n[i], CM.get(f[i]&CF), v[i] or None)
                           for i in range(len(n))]
                cnfargs.extend(upgargs)
                upgargs.append(obstup)
            else:
                upgargs = [obstup]

            pkg = self.buildPackage((Pkg, name, versionarch),
                                    prvargs, reqargs, upgargs, cnfargs)
            pkg.loaders[self] = offset
            pkg._group = h[rpm.RPMTAG_GROUP]
            self._offsets[offset] = pkg

class RPMHeaderListLoader(RPMHeaderLoader):

    def __init__(self, filename, baseurl, count=None):
        RPMHeaderLoader.__init__(self)
        self._filename = filename
        self._baseurl = baseurl
        self._count = count

    def getLoadSteps(self):
        if self._count is None:
            return len(rpm.readHeaderListFromFile(self._filename))
        return self._count

    def getHeaders(self, prog):
        file = open(self._filename)
        h, offset = rpm.readHeaderFromFD(file.fileno())
        while h:
            yield h, offset
            h, offset = rpm.readHeaderFromFD(file.fileno())
            prog.add(1)
            prog.show()
        file.close()

    def getHeader(self, pkg):
        file = open(self._filename)
        file.seek(pkg.loaders[self])
        h, offset = rpm.readHeaderFromFD(file.fileno())
        file.close()
        return h

    def getURL(self):
        return self._baseurl

    def getFileName(self, info):
        h = info._h
        return "%s-%s-%s.%s.rpm" % (h[rpm.RPMTAG_NAME],
                                    h[rpm.RPMTAG_VERSION],
                                    h[rpm.RPMTAG_RELEASE],
                                    h[rpm.RPMTAG_ARCH])

    def getSize(self, info):
        return None

    def getMD5(self, info):
        return None

    def loadFileProvides(self, fndict):
        file = open(self._filename)
        h, offset = rpm.readHeaderFromFD(file.fileno())
        bfp = self.buildFileProvides
        while h:
            for fn in h[1027]: # RPMTAG_OLDFILENAMES
                if fn in fndict and offset in self._offsets:
                    bfp(self._offsets[offset], (RPMProvides, fn))
            h, offset = rpm.readHeaderFromFD(file.fileno())
        file.close()

class RPMPackageListLoader(RPMHeaderListLoader):

    def getFileName(self, info):
        h = info._h
        filename = h[CRPMTAG_FILENAME]
        if not filename:
            raise Error, "Package list with no CRPMTAG_FILENAME tag"
        directory = h[CRPMTAG_DIRECTORY]
        if directory:
            filename = os.path.join(directory, filename)
        return filename

    def getSize(self, info):
        return info._h[CRPMTAG_FILESIZE]

    def getMD5(self, info):
        return info._h[CRPMTAG_MD5]

class URPMILoader(RPMHeaderListLoader):

    def getFileName(self, info):
        h = info._h
        filename = h[CRPMTAG_FILENAME]
        if not filename:
            raise Error, "Package list with no CRPMTAG_FILENAME tag"
        return os.path.join(h[rpm.RPMTAG_ARCH], filename)

    def getSize(self, info):
        return info._h[CRPMTAG_FILESIZE]

    def getMD5(self, info):
        return None

class RPMDBLoader(RPMHeaderLoader):

    def __init__(self):
        RPMHeaderLoader.__init__(self)
        self.setInstalled(True)

    def getLoadSteps(self):
        return 1

    def getHeaders(self, prog):
        ts = rpm.ts(sysconf.get("rpm-root", "/"))
        mi = ts.dbMatch()
        for h in mi:
            if h[1000] != "gpg-pubkey": # RPMTAG_NAME
                yield h, mi.instance()
            prog.addTotal(1)
            prog.add(1)
            prog.show()
        prog.add(1)

    def getHeader(self, pkg):
        ts = rpm.ts(sysconf.get("rpm-root", "/"))
        mi = ts.dbMatch(0, pkg.loaders[self])
        return mi.next()

    def getURL(self):
        return None

    def getFileName(self, info):
        return None

    def getSize(self, info):
        return None

    def getMD5(self, info):
        return None

    def loadFileProvides(self, fndict):
        ts = rpm.ts(sysconf.get("rpm-root", "/"))
        bfp = self.buildFileProvides
        for fn in fndict.keys():
            mi = ts.dbMatch(1117, fn) # RPMTAG_BASENAMES
            h = mi.next()
            while h:
                i = mi.instance()
                if i in self._offsets:
                    bfp(self._offsets[i], (RPMProvides, fn))
                h = mi.next()

class RPMDirLoader(RPMHeaderLoader):

    def __init__(self, dir, filename=None):
        RPMHeaderLoader.__init__(self)
        self._dir = os.path.abspath(dir)
        if filename:
            self._filenames = [filename]
        else:
            self._filenames = [x for x in os.listdir(dir)
                               if x.endswith(".rpm") and
                               not x.endswith(".src.rpm")]

    def getLoadSteps(self):
        return len(self._filenames)

    def getHeaders(self, prog):
        ts = rpm.ts()
        for i, filename in enumerate(self._filenames):
            file = open(os.path.join(self._dir, filename))
            h = ts.hdrFromFdno(file.fileno())
            file.close()
            yield (h, i)
            prog.add(1)
            prog.show()

    def getHeader(self, pkg):
        filename = self._filenames[pkg.loaders[self]]
        file = open(os.path.join(self._dir, filename))
        ts = rpm.ts()
        h = ts.hdrFromFdno(file.fileno())
        file.close()
        return h

    def getURL(self):
        return "file:///"

    def getFileName(self, info):
        pkg = info.getPackage()
        filename = self._filenames[pkg.loaders[self]]
        filepath = os.path.join(self._dir, filename)
        while filepath.startswith("/"):
            filepath = filepath[1:]
        return filepath

    def getSize(self, info):
        pkg = info.getPackage()
        filename = self._filenames[pkg.loaders[self]]
        return os.path.getsize(os.path.join(self._dir, filename))

    def getMD5(self, info):
        # Could compute it now, but why?
        return None

    def loadFileProvides(self, fndict):
        ts = rpm.ts()
        bfp = self.buildFileProvides
        for i, filename in enumerate(self._filenames):
            if i not in self._offsets:
                continue
            file = open(os.path.join(self._dir, filename))
            h = ts.hdrFromFdno(file.fileno())
            file.close()
            for fn in h[1027]: # RPMTAG_OLDFILENAMES
                if fn in fndict:
                    bfp(self._offsets[i], (RPMProvides, fn))

class RPMFileChannel(FileChannel):

    def __init__(self, filename):
        FileChannel.__init__(self, filename)
        dirname, basename = os.path.split(filename)
        self.setInfo("loader", RPMDirLoader(dirname, basename))

def createFileChannel(filename):
    if filename.endswith(".rpm") and not filename.endswith(".src.rpm"):
        return RPMFileChannel(filename)
    return None

hooks.register("create-file-channel", createFileChannel)

# vim:ts=4:sw=4:et

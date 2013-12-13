#
# Copyright (c) 2005-2007 Canonical
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
from smart.backends.rpm.rpmver import checkver, splitarch
from smart.util.strtools import globdistance
from smart.cache import Loader, PackageInfo
from smart.channel import FileChannel
from smart.backends.rpm.base import *
from smart.progress import Progress
from smart import *
import locale
import stat
import os
from datetime import datetime
import time

try:
    import rpmhelper
except ImportError:
    rpmhelper = None

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

ENCODINGS = ["utf8", "iso-8859-1"]


def get_header_filenames(header):
    filenames = header[rpm.RPMTAG_OLDFILENAMES]
    if not filenames and header[rpm.RPMTAG_BASENAMES]:
        dirindexes = header[rpm.RPMTAG_DIRINDEXES]
        if type(dirindexes) != list:
            dirindexes = [dirindexes]
        dirnames = header[rpm.RPMTAG_DIRNAMES]
        if type(dirnames) != list:
            dirnames = [dirnames]
        basenames = header[rpm.RPMTAG_BASENAMES]
        if type(basenames) != list:
            basenames = [basenames]
        filenames = [dirnames[dirindexes[i]] + basename
                     for i, basename in enumerate(basenames)]
    elif type(filenames) != list:
        filenames = [filenames]
    return filenames


class RPMHeaderPackageInfo(PackageInfo):

    class LazyHeader(object):
        def __get__(self, obj, type):
            obj._h = obj._loader.getHeader(obj._package)
            return obj._h

    _h = LazyHeader()

    def __init__(self, package, loader, order=0):
        PackageInfo.__init__(self, package, order)
        self._loader = loader
        self._path = None
        self._change = None

    def getReferenceURLs(self):
        url = self._h[rpm.RPMTAG_URL]
        if url:
            return [url]
        return []

    def getURLs(self):
        url = self._loader.getURL()
        if url:
            return [os.path.join(url, self._loader.getFileName(self))]
        return []

    def getSize(self, url):
        return self._loader.getSize(self)

    def getMD5(self, url):
        return self._loader.getMD5(self)

    def getBuildTime(self):
        return self._h[rpm.RPMTAG_BUILDTIME]

    def getInstalledSize(self):
        return self._h[rpm.RPMTAG_SIZE]

    def _getHeaderString(self, tag):
        result = self._h and self._h[tag] or u""
        if result:
            if type(result) == list:
                # Must have an element, or the check above would fail.
                result = result[0]
            for encoding in ENCODINGS:
                try:
                    result = result.decode(encoding)
                except UnicodeDecodeError:
                    continue
                break
        return result

    def _getHeaderArray(self, tag):
        result = self._h and self._h[tag] or []
        if result:
            if type(result) != list:
                result = [result]
            for i in range(len(result)):
                if type(result[i]) == str:
                    for encoding in ENCODINGS:
                        try:
                            result[i] = result[i].decode(encoding)
                        except UnicodeDecodeError:
                            continue
                        break
        return result

    def getDescription(self):
        return self._getHeaderString(rpm.RPMTAG_DESCRIPTION)

    def getSummary(self):
        return self._getHeaderString(rpm.RPMTAG_SUMMARY)

    def getSource(self):
        sourcerpm = self._getHeaderString(rpm.RPMTAG_SOURCERPM)
        sourcerpm = sourcerpm.replace(".src", "")
        sourcerpm = sourcerpm.replace(".nosrc", "")
        return sourcerpm.replace(".rpm", "")
    
    def getGroup(self):
        s = self._loader.getGroup(self._package)
        for encoding in ENCODINGS:
            try:
                s = s.decode(encoding)
            except UnicodeDecodeError:
                continue
            break
        else:
            s = ""
        return s

    def getLicense(self):
        return self._getHeaderString(rpm.RPMTAG_LICENSE)

    def getChangeLog(self):
        if self._change is None:
            logtime = self._getHeaderArray(rpm.RPMTAG_CHANGELOGTIME)
            self._change = []
            if len(logtime) > 0:
                logname = self._getHeaderArray(rpm.RPMTAG_CHANGELOGNAME)
                change = self._getHeaderArray(rpm.RPMTAG_CHANGELOGTEXT)
                for i in range(len(change)):
                    self._change.append(datetime.fromtimestamp(logtime[i]).strftime("%Y-%m-%d")+"  "+ logname[i])
                    self._change.append("  " + change[i])
        return self._change

    def getPathList(self):
        if self._path is None:
            paths = get_header_filenames(self._h)
            modes = self._h[rpm.RPMTAG_FILEMODES]
            if modes:
                if type(modes) != list:
                    modes = [modes]
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

    __stateversion__ = Loader.__stateversion__+1
 
    COMPFLAGS = rpm.RPMSENSE_EQUAL|rpm.RPMSENSE_GREATER|rpm.RPMSENSE_LESS

    COMPMAP = { rpm.RPMSENSE_EQUAL:   "=",
                rpm.RPMSENSE_LESS:    "<",
                rpm.RPMSENSE_GREATER: ">",
                rpm.RPMSENSE_EQUAL|rpm.RPMSENSE_LESS:    "<=",
                rpm.RPMSENSE_EQUAL|rpm.RPMSENSE_GREATER: ">=" }

    def __init__(self):
        Loader.__init__(self)
        self._infoorder = 0
        self._offsets = {}
        self._groups = {}

    def getHeaders(self, prog):
        return []

    def getInfo(self, pkg):
        return RPMHeaderPackageInfo(pkg, self, self._infoorder)

    def getGroup(self, pkg):
        return self._groups[pkg]

    def reset(self):
        Loader.reset(self)
        self._offsets.clear()
        self._groups.clear()

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
            if h[1106]: # RPMTAG_SOURCEPACKAGE
                continue
            arch = h[1022] # RPMTAG_ARCH
            if getArchScore(arch) == 0:
                continue

            name = h[1000] # RPMTAG_NAME
            epoch = h[1003] # RPMTAG_EPOCH
            if epoch and epoch != "0":
                # RPMTAG_VERSION, RPMTAG_RELEASE
                version = "%s:%s-%s" % (epoch, h[1001], h[1002])
            else:
                # RPMTAG_VERSION, RPMTAG_RELEASE
                version = "%s-%s" % (h[1001], h[1002])
            versionarch = "%s@%s" % (version, arch)

            n = h[1047] # RPMTAG_PROVIDENAME
            v = h[1113] # RPMTAG_PROVIDEVERSION
            prvdict = {}
            for i in range(len(n)):
                ni = n[i]
                if not ni.startswith("config("):
                    vi = v[i]
                    if vi and vi[:2] == "0:":
                        vi = vi[2:]
                    if ni == name and checkver(vi, version):
                        prvdict[(NPrv, intern(ni), versionarch)] = True
                    else:
                        prvdict[(Prv, intern(ni), vi or None)] = True
            prvargs = prvdict.keys()

            n = h[1049] # RPMTAG_REQUIRENAME
            if n:
                f = h[1048] # RPMTAG_REQUIREFLAGS
                v = h[1050] # RPMTAG_REQUIREVERSION
                if f == None:
                    f = [0]
                elif type(f) != list:
                    f = [f]
                recdict = {}
                reqdict = {}
                for i in range(len(n)):
                    ni = n[i]
                    if ni[:7] not in ("rpmlib(", "config("):
                        vi = v[i] or None
                        if vi and vi[:2] == "0:":
                            vi = vi[2:]
                        r = CM.get(f[i]&CF)
                        if not ((r is None or "=" in r) and
                                (Prv, ni, vi) in prvdict or
                                system_provides.match(ni, r, vi)):
                            # RPMSENSE_PREREQ |
                            # RPMSENSE_SCRIPT_PRE |
                            # RPMSENSE_SCRIPT_PREUN |
                            # RPMSENSE_SCRIPT_POST |
                            # RPMSENSE_SCRIPT_POSTUN == 7744
                            if (f[i]&rpm.RPMSENSE_MISSINGOK):
                                recdict[(f[i]&7744 and PreReq or Req,
                                         intern(ni), r, vi)] = True
                            else:
                                reqdict[(f[i]&7744 and PreReq or Req,
                                         intern(ni), r, vi)] = True
                recargs = collapse_libc_requires(recdict.keys())
                reqargs = collapse_libc_requires(reqdict.keys())
            else:
                recargs = None
                reqargs = None

            n = h[1054] # RPMTAG_CONFLICTNAME
            if n:
                f = h[1053] # RPMTAG_CONFLICTFLAGS
                v = h[1055] # RPMTAG_CONFLICTVERSION
                if f == None:
                    f = [0]
                elif type(f) != list:
                    f = [f]
                cnfargs = []
                for i in range(len(n)):
                    vi = v[i] or None
                    if vi and vi[:2] == "0:":
                        vi = vi[2:]
                    cnfargs.append((Cnf, n[i], CM.get(f[i]&CF), vi))
            else:
                cnfargs = []

            obstup = (Obs, name, '<', versionarch)

            n = h[1090] # RPMTAG_OBSOLETENAME
            if n:
                f = h[1114] # RPMTAG_OBSOLETEFLAGS
                v = h[1115] # RPMTAG_OBSOLETEVERSION
                if f == None:
                    f = [0]
                elif type(f) != list:
                    f = [f]
                upgargs = []
                for i in range(len(n)):
                    try:
                        vi = v[i] or None
                    except TypeError:
                        vi = None
                        pass
                    if vi and vi[:2] == "0:":
                        vi = vi[2:]
                    upgargs.append((Obs, n[i], CM.get(f[i]&CF), vi))
                cnfargs.extend(upgargs)
                upgargs.append(obstup)
            else:
                upgargs = [obstup]

            disttag = h[1155] # RPMTAG_DISTTAG
            distepoch = h[1218] # RPMTAG_DISTEPOCH
            if disttag:
                distversion = "%s-%s" % (version, disttag)
                if distepoch:
                    distversion += distepoch
                versionarch = "%s@%s" % (distversion, arch)

            pkg = self.buildPackage((Pkg, name, versionarch),
                                    prvargs, reqargs, upgargs, cnfargs, recargs)
            pkg.loaders[self] = offset
            self._offsets[offset] = pkg
            self._groups[pkg] = intern(h[rpm.RPMTAG_GROUP])

    def search(self, searcher):
        ic = searcher.ignorecase
        for h, offset in self.getHeaders(Progress()):
            pkg = self._offsets.get(offset)
            if not pkg:
                continue

            ratio = 0
            if searcher.url:
                refurl = h[rpm.RPMTAG_URL]
                if refurl:
                    for url, cutoff in searcher.url:
                        _, newratio = globdistance(url, refurl, cutoff, ic)
                        if newratio > ratio:
                            ratio = newratio
                            if ratio == 1:
                                break
            if ratio == 1:
                searcher.addResult(pkg, ratio)
                continue
            if searcher.path:
                paths = get_header_filenames(h)
                if paths:
                    for spath, cutoff in searcher.path:
                        for path in paths:
                            _, newratio = globdistance(spath, path, cutoff, ic)
                            if newratio > ratio:
                                ratio = newratio
                                if ratio == 1:
                                    break
                        else:
                            continue
                        break
            if ratio == 1:
                searcher.addResult(pkg, ratio)
                continue
            if searcher.group:
                group = self._groups[pkg]
                for pat in searcher.group:
                    if pat.search(group):
                        ratio = 1
                        break
            if ratio == 1:
                searcher.addResult(pkg, ratio)
                continue
            if searcher.summary:
                summary = h[rpm.RPMTAG_SUMMARY]
                for pat in searcher.summary:
                    if pat.search(summary):
                        ratio = 1
                        break
            if ratio == 1:
                searcher.addResult(pkg, ratio)
                continue
            if searcher.description:
                description = h[rpm.RPMTAG_DESCRIPTION]
                for pat in searcher.description:
                    if pat.search(description):
                        ratio = 1
                        break
            if ratio:
                searcher.addResult(pkg, ratio)

class RPMHeaderListLoader(RPMHeaderLoader):

    def __init__(self, filename, baseurl, count=None):
        RPMHeaderLoader.__init__(self)
        self._filename = filename
        self._baseurl = baseurl
        self._count = count

        self._checkRPM()

    def __getstate__(self):
        state = RPMHeaderLoader.__getstate__(self)
        if "_hdl" in state:
            del state["_hdl"]
        return state

    def __setstate__(self, state):
        RPMHeaderLoader.__setstate__(self, state)
        self._checkRPM()

    def _checkRPM(self):
        if not hasattr(rpm, "readHeaderFromFD"):

            if (not hasattr(self.__class__, "WARNED") and
                sysconf.get("no-rpm-readHeaderFromFD", 0) < 3):

                self.__class__.WARNED = True
                sysconf.set("no-rpm-readHeaderFromFD",
                            sysconf.get("no-rpm-readHeaderFromFD", 0)+1)
                iface.warning(_("Your rpm module has no support for "
                                "readHeaderFromFD()!\n"
                                "As a consequence, Smart will consume "
                                "extra memory."))

            self.__class__.getHeaders = self.getHeadersHDL.im_func
            self.__class__.getHeader = self.getHeaderHDL.im_func
            self.__class__.loadFileProvides = self.loadFileProvidesHDL.im_func

            self._hdl = rpm.readHeaderListFromFile(self._filename)

    def getLoadSteps(self):
        if self._count is None:
            if hasattr(rpm, "readHeaderFromFD"):
                return os.path.getsize(self._filename)/2500
            else:
                return len(rpm.readHeaderListFromFile(self._filename))
        return self._count

    def getHeaders(self, prog):
        file = open(self._filename)
        lastoffset = mod = 0
        h, offset = rpm.readHeaderFromFD(file.fileno())
        if self._count:
            while h:
                yield h, offset
                h, offset = rpm.readHeaderFromFD(file.fileno())
                if offset:
                    prog.add(1)
                    prog.show()
        else:
            while h:
                yield h, offset
                h, offset = rpm.readHeaderFromFD(file.fileno())
                if offset:
                    div, mod = divmod(offset-lastoffset+mod, 2500)
                    lastoffset = offset
                    prog.add(div)
                    prog.show()
        file.close()

    def getHeadersHDL(self, prog):
        for offset, h in enumerate(self._hdl):
            yield h, offset
            prog.add(1)
            prog.show()

    def getHeader(self, pkg):
        file = open(self._filename)
        file.seek(pkg.loaders[self])
        h, offset = rpm.readHeaderFromFD(file.fileno())
        file.close()
        return h

    def getHeaderHDL(self, pkg):
        return self._hdl[pkg.loaders[self]]

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
            for fn in get_header_filenames(h):
                fn = fndict.get(fn)
                if fn and offset in self._offsets:
                    bfp(self._offsets[offset], (RPMProvides, fn, None))
            h, offset = rpm.readHeaderFromFD(file.fileno())
        file.close()

    def loadFileProvidesHDL(self, fndict):
        bfp = self.buildFileProvides
        for offset, h in enumerate(self._hdl):
            for fn in get_header_filenames(h):
                fn = fndict.get(fn)
                if fn and offset in self._offsets:
                    bfp(self._offsets[offset], (RPMProvides, fn, None))

class RPMPackageListLoader(RPMHeaderListLoader):

    def getFileName(self, info):
        h = info._h
        filename = h[CRPMTAG_FILENAME]
        if not filename:
            raise Error, _("Package list with no CRPMTAG_FILENAME tag")
        directory = h[CRPMTAG_DIRECTORY]
        if directory:
            filename = os.path.join(directory, filename)
        return filename

    def getSize(self, info):
        return info._h[CRPMTAG_FILESIZE]

    def getMD5(self, info):
        return info._h[CRPMTAG_MD5]

class URPMILoader(RPMHeaderListLoader):

    def __init__(self, filename, baseurl, listfile):
        RPMHeaderListLoader.__init__(self, filename, baseurl)
        self._prefix = {}
        self._flagdict = None

    def setErrataFlags(self, flagdict):
        self._flagdict = flagdict
    
    def buildPackage(self, pkgargs, prvargs, reqargs, upgargs, cnfargs, recargs):
        pkg = Loader.buildPackage(self, pkgargs, prvargs, reqargs, upgargs, cnfargs, recargs)
        name = pkgargs[1]
        if hasattr(self, '_flagdict') and self._flagdict and name in self._flagdict:
            if sysconf.getReadOnly():
                pkgconf.setFlag(self._flagdict[name], name, "=", pkgargs[2])
        return pkg

    def getFileName(self, info):
        h = info._h
        filename = h[CRPMTAG_FILENAME]
        if not filename:
            raise Error, _("Package list with no CRPMTAG_FILENAME tag")
        if filename in self._prefix:
            filename = os.path.join(self._prefix[filename], filename)
        return filename

    def getSize(self, info):
        return info._h[CRPMTAG_FILESIZE]

    def getMD5(self, info):
        return None

class RPMDBLoader(RPMHeaderLoader):

    def __init__(self):
        RPMHeaderLoader.__init__(self)
        self.setInstalled(True)
        self._infoorder = -100

    def getLoadSteps(self):
        # Estimate, since there's no other good way to do it.
        return 1000

    def getHeaders(self, prog):
        mi = getTS().dbMatch()
        total = left = self.getLoadSteps()
        for h in mi:
            if h[1000] != "gpg-pubkey": # RPMTAG_NAME
                yield h, mi.instance()
            if left == 0:
                prog.addTotal(1)
            else:
                left -= 1
            prog.add(1)
            prog.show()
        prog.add(left)

    def getHeader(self, pkg):
        if rpmhelper:
            mi = rpmhelper.dbMatch(getTS(), 0, pkg.loaders[self])
        else:
            mi = getTS().dbMatch(0, pkg.loaders[self])
        try:
            return mi.next()
        except StopIteration:
            class NullHeader(object):
                def __getitem__(self, key):
                    return None
            return NullHeader()

    def getURL(self):
        return None

    def getFileName(self, info):
        return None

    def getSize(self, info):
        return None

    def getMD5(self, info):
        return None

    def loadFileProvides(self, fndict):
        ts = getTS()
        bfp = self.buildFileProvides
        for fn in fndict:
            mi = ts.dbMatch(1117, fn) # RPMTAG_BASENAMES
            try:
                h = mi.next()
                while h:
                    i = mi.instance()
                    if i in self._offsets:
                        bfp(self._offsets[i], (RPMProvides, fn, None))
                    h = mi.next()
            except StopIteration:
                pass

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
        ts = getTS()
        for i, filename in enumerate(self._filenames):
            filepath = os.path.join(self._dir, filename)
            file = open(filepath)
            try:
                h = ts.hdrFromFdno(file.fileno())
            except rpm.error, e:
                iface.error("%s: %s" % (os.path.basename(filepath), e))
            else:
                yield (h, i)
            file.close()
            prog.add(1)
            prog.show()

    def getHeader(self, pkg):
        filename = self._filenames[pkg.loaders[self]]
        filepath = os.path.join(self._dir, filename)
        file = open(filepath)
        ts = getTS()
        try:
            h = ts.hdrFromFdno(file.fileno())
        except rpm.error, e:
            iface.error("%s: %s" % (os.path.basename(filepath), e))
            h = None
        file.close()
        return h

    def getURL(self):
        return "file:///"

    def getFileName(self, info):
        pkg = info.getPackage()
        filename = self._filenames[pkg.loaders[self]]
        filepath = os.path.join(self._dir, filename)
        return filepath.lstrip("/")

    def getSize(self, info):
        pkg = info.getPackage()
        filename = self._filenames[pkg.loaders[self]]
        return os.path.getsize(os.path.join(self._dir, filename))

    def getMD5(self, info):
        # Could compute it now, but why?
        return None

    def loadFileProvides(self, fndict):
        ts = getTS()
        bfp = self.buildFileProvides
        for i, filename in enumerate(self._filenames):
            if i not in self._offsets:
                continue
            filepath = os.path.join(self._dir, filename)
            file = open(filepath)
            try:
                h = ts.hdrFromFdno(file.fileno())
            except rpm.error, e:
                file.close()
                iface.error("%s: %s" % (os.path.basename(filepath), e))
            else:
                file.close()
                for fn in get_header_filenames(h):
                    fn = fndict.get(fn)
                    if fn:
                        bfp(self._offsets[i], (RPMProvides, fn, None))

class RPMFileChannel(FileChannel):

    def fetch(self, fetcher, progress):
        digest = os.path.getmtime(self._filename)
        if digest == self._digest:
            return True
        self.removeLoaders()
        dirname, basename = os.path.split(self._filename)
        loader = RPMDirLoader(dirname, basename)
        loader.setChannel(self)
        self._loaders.append(loader)
        self._digest = digest
        return True

def createFileChannel(filename):
    if filename.endswith(".rpm") and not filename.endswith(".src.rpm"):
        return RPMFileChannel(filename)
    return None

hooks.register("create-file-channel", createFileChannel)

def enablePsyco(psyco):
    psyco.bind(RPMHeaderLoader.load)
    psyco.bind(RPMHeaderLoader.search)
    psyco.bind(RPMHeaderListLoader.getHeaders)
    psyco.bind(RPMHeaderListLoader.getHeadersHDL)
    psyco.bind(RPMHeaderListLoader.loadFileProvides)
    psyco.bind(RPMHeaderListLoader.loadFileProvidesHDL)
    psyco.bind(RPMDirLoader.getHeaders)
    psyco.bind(RPMDirLoader.loadFileProvides)
    psyco.bind(RPMDBLoader.getHeaders)
    psyco.bind(RPMDBLoader.loadFileProvides)

hooks.register("enable-psyco", enablePsyco)

# vim:ts=4:sw=4:et

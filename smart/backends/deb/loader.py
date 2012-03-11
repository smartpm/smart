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
from smart.cache import Loader, PackageInfo
from smart.util.strtools import globdistance
from smart.util.tagfile import TagFile
from smart.channel import FileChannel
from smart.backends.deb.debver import parserelation, parserelations
from smart.backends.deb.base import *
from smart.progress import Progress
from smart import *
from io import BytesIO
import locale
import stat
import os


def decode(s):
    if isinstance(s, str):
        return s
    return str(s, "UTF-8", "replace")


class DebPackageInfo(PackageInfo):

    class LazyDict(object):
        def __get__(self, obj, type):
            obj._dict = obj._loader.getDict(obj._package)
            return obj._dict

    _dict = LazyDict()

    def __init__(self, package, loader):
        PackageInfo.__init__(self, package)
        self._loader = loader

    def getReferenceURLs(self):
        homepage = self._dict.get(b"homepage")
        if homepage:
            return [homepage]
        description = self._dict.get(b"description")
        for line in description.splitlines():
            if line.startswith("Web site:"):
                return [line[9:].strip()]
        return []

    def getURLs(self):
        url = self._loader.getURL()
        if url:
            return [os.path.join(url, self._loader.getFileName(self).decode())]
        return []

    def getSize(self, url):
        return self._loader.getSize(self)

    def getMD5(self, url):
        return self._dict.get(b"md5sum")

    def getSHA(self, url):
        return self._dict.get(b"sha1")

    def getSHA256(self, url):
        return self._dict.get(b"sha256")

    def getInstalledSize(self):
        size = self._dict.get(b"installed-size")
        if size:
            try:
                return int(size)*1024
            except ValueError:
                pass
        return None

    def getDescription(self):
        description = self._dict.get(b"description")
        if description:
            toks = description.split(b"\n", 1)
            if len(toks) == 2:
                return decode(toks[1])
        return ""

    def getSummary(self):
        description = self._dict.get(b"description")
        if description:
            
            return decode(description.split(b"\n", 1)[0])
        return ""

    def getSource(self):
        import re
        sourcename = self._dict.get(b"source") or self._package.name
        m = re.match(r"([a-z0-9+-.]+)\s?\((.+)\)", sourcename.decode())
        if not m:
            sourcename = "%s_%s" % (sourcename.decode(), self._package.version.decode())
        else:
            sourcename = "%s_%s" % m.groups()
        return sourcename
    
    def getGroup(self):
        return decode(self._loader.getSection(self._package))

    def getLicense(self):
        return ""

    def getChangeLog(self):
        self._change = self._loader.getChanges(self)
        return self._change

    def getPathList(self):
        self._paths = self._loader.getPaths(self)
        return list(self._paths.keys())

    def pathIsDir(self, path):
        return self._paths[path] == "d"

    def pathIsFile(self, path):
        return self._paths[path] == "f"

class DebTagLoader(Loader):

    __stateversion__ = Loader.__stateversion__+2

    def __init__(self, baseurl=None):
        Loader.__init__(self)
        self._baseurl = baseurl
        self._sections = {}

    def getURL(self):
        return self._baseurl

    def getSection(self, pkg):
        return self._sections[pkg]

    def getInfo(self, pkg):
        return DebPackageInfo(pkg, self)

    def reset(self):
        Loader.reset(self)

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
        Brk = DebBreaks
        prog = iface.getProgress(self._cache)
        inst = self.getInstalled()
        sysarch = DEBARCH
        for section, offset in self.getSections(prog):
            arch = section.get(b"architecture").decode()
            if arch and arch != sysarch and arch != "all":
                continue

            if inst:
                try:
                    want, flag, status = section.get(b"status", b"").split()
                except ValueError:
                    continue
                if status != b"installed":
                    continue
            
            name = section.get(b"package")
            version = section.get(b"version")

            prvargs = [(NPrv, name, version)]
            prvdict = {name: True}
            value = section.get(b"provides")
            if value:
                for prvname in value.split(b","):
                    prvname = prvname.strip()
                    prvargs.append((Prv, prvname, None))
                    prvdict[prvname] = True

            reqargs = []
            value = section.get(b"depends")
            if value:
                for relation in parserelations(value):
                    if type(relation) is not list:
                        n, r, v = relation
                        reqargs.append((Req, n, r, v))
                    else:
                        reqargs.append((OrReq, tuple(relation)))
            value = section.get(b"pre-depends")
            if value:
                for relation in parserelations(value):
                    if type(relation) is not list:
                        n, r, v = relation
                        reqargs.append((PreReq, n, r, v))
                    else:
                        reqargs.append((OrPreReq, tuple(relation)))

            upgargs = [(Upg, name, b'<', version)]

            cnfargs = []
            value = section.get(b"conflicts")
            if value:
                for relation in parserelations(value):
                    n, r, v = relation
                    cnfargs.append((Cnf, n, r, v))

            value = section.get(b"breaks")
            if value:
                for relation in parserelations(value):
                    n, r, v = relation
                    cnfargs.append((Brk, n, r, v))

            newargs = []
            for args in reqargs:
                req = args[0](*args[1:])
                if not system_provides.matches(req):
                    newargs.append(args)
            reqargs = newargs

            pkg = self.buildPackage((Pkg, name, version),
                                    prvargs, reqargs, upgargs, cnfargs)
            pkg.loaders[self] = offset
            self._sections[pkg] = section.get(b"section", "")

    def search(self, searcher):
        offsets = {}
        for pkg in self._packages:
            offsets[pkg.loaders[self]] = pkg

        for section, offset in self.getSections(Progress()):
            pkg = offsets.get(offset)
            if not pkg:
                continue

            ratio = 0
            if searcher.group:
                group = self._sections[pkg]
                for pat in searcher.group:
                    if pat.search(group):
                        ratio = 1
                        break
            if ratio == 1:
                searcher.addResult(pkg, ratio)
                continue

            if searcher.summary or searcher.description:
                toks = section.get(b"description", "").split("\n", 1)
                if len(toks) == 2:
                    summary, description = toks
                else:
                    summary, description = toks[0], ""

            if searcher.summary:
                for pat in searcher.summary:
                    if pat.search(summary):
                        ratio = 1
                        break
            if ratio == 1:
                searcher.addResult(pkg, ratio)
                continue
            if searcher.description:
                for pat in searcher.description:
                    if pat.search(description):
                        ratio = 1
                        break
            if ratio:
                searcher.addResult(pkg, ratio)

    def getSections(self, prog):
        raise TypeError("Subclasses of DebTagLoader must " \
                         "implement the getSections() method")

    def getDict(self, pkg):
        raise TypeError("Subclasses of DebTagLoader must " \
                         "implement the getDict() method")

    def getFileName(self, info):
        raise TypeError("Subclasses of DebTagLoader must " \
                         "implement the getFileName() method")

    def getSize(self, info):
        raise TypeError("Subclasses of DebTagLoader must " \
                         "implement the getFileName() method")

    def getChanges(self, info):
        return []

    def getPaths(self, info):
        return {}


class DebTagFileLoader(DebTagLoader):

    # It's important for the default to be here so that old pickled
    # instances which don't have these attributes still work fine.
    _filelistsname = None
    _changelogname = None

    def __init__(self, filename, baseurl=None, filelistsname="", changelogname=""):
        DebTagLoader.__init__(self, baseurl)
        self._filename = filename
        self._filelistsname = filelistsname
        self._changelogname = changelogname
        self._tagfile = TagFile(self._filename.encode())

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

    def getDict(self, pkg):
        self._tagfile.setOffset(pkg.loaders[self])
        self._tagfile.advanceSection()
        return self._tagfile.copy()

    def getFileName(self, info):
        return info._dict.get(b"filename")

    def getSize(self, info):
        size = info._dict.get(b"size")
        if size:
            return int(size)
        return None

    def getChanges(self, info):
        if not self._changelogname:
            return []
        changes = []
        for basename in ["changelog.Debian.gz", "changelog.gz"]:
            filename = os.path.join(self._changelogname, info._package.name, basename)
            if os.path.isfile(filename):
                if filename.endswith(".gz"):
                    import gzip
                    file = gzip.open(filename)
                else:
                    file = open(filename, "rb")
                line = file.readline()
                while True:
                    if not line:
                        break
                    changes.append(line.strip())
                    line = file.readline()
                    change = ""
                    while line.startswith(" ") or (line == "\n"):
                        change += line
                        line = file.readline()
                    changes.append(change)
                break
        return changes

    def getPaths(self, info):
        if not self._filelistsname:
            listname = os.path.join(os.path.dirname(self._filename), "info", info._package.name+".list")
        else:
            listname = os.path.join(self._filelistsname, info._package.name+".list")
        paths = {}
        if os.path.isfile(listname):
            md5name = listname[:-4]+"md5sums"
            dirs = {}
            if os.path.isfile(md5name):
                for line in open(md5name):
                    toks = line.split()
                    if len(toks) == 2:
                        dirs["/"+toks[1]] = True
            for line in open(listname):
                path = line.strip()
                if path:
                    paths[path] = path in dirs and "d" or "f"
            if "/." in paths:
                del paths["/."]
        return paths

class DebDirLoader(DebTagLoader):

    def __init__(self, dir, filename=None):
        DebTagLoader.__init__(self, "file:///")
        self._dir = os.path.abspath(dir)
        if filename:
            self._filenames = [filename]
        else:
            self._filenames = [x for x in os.listdir(dir)
                                  if x.endswith(".deb")]

    def getLoadSteps(self):
        return len(self._filenames)

    def getSections(self, prog):
        for i, filename in enumerate(self._filenames):
            filepath = os.path.join(self._dir, filename)
            control = getControl(filepath)
            tf = TagFile(BytesIO(control))
            tf.advanceSection()
            yield (tf, i)
            prog.add(1)
            prog.show()

    def getDict(self, pkg):
        filename = self._filenames[pkg.loaders[self]]
        filepath = os.path.join(self._dir, filename)
        control = getControl(filepath)
        tf = TagFile(BytesIO(control))
        tf.advanceSection()
        return tf

    def getFileName(self, info):
        pkg = info.getPackage()
        filename = self._filenames[pkg.loaders[self]]
        filepath = os.path.join(self._dir, filename)
        return filepath.lstrip("/")

    def getSize(self, info):
        pkg = info.getPackage()
        filename = self._filenames[pkg.loaders[self]]
        return os.path.getsize(os.path.join(self._dir, filename))

class DebFileChannel(FileChannel):

    def fetch(self, fetcher, progress):
        digest = os.path.getmtime(self._filename)
        if digest == self._digest:
            return True
        self.removeLoaders()
        dirname, basename = os.path.split(self._filename)
        loader = DebDirLoader(dirname, basename)
        loader.setChannel(self)
        self._loaders.append(loader)
        self._digest = digest
        return True

def createFileChannel(filename):
    if filename.endswith(".deb"):
        return DebFileChannel(filename)
    return None

hooks.register("create-file-channel", createFileChannel)

def getControl(filename):
    from io import BytesIO
    from tarfile import TarFile
    file = open(filename, "rb")
    if file.read(8) != b"!<arch>\n":
        raise ValueError("Invalid file")
    while True:
        name = file.read(16)
        date = file.read(12)
        uid = file.read(6)
        gid = file.read(6)
        mode = file.read(8)
        size = file.read(10)
        magic = file.read(2)
        if name == b"control.tar.gz  ":
            data = file.read(int(size))
            sio = BytesIO(data)
            tf = TarFile.gzopen("", fileobj=sio)
            try:
                control = tf.extractfile("./control")
            except KeyError:
                control = tf.extractfile("control")
            return control.read()
        else:
            file.seek(int(size), 1)
    return None

def enablePsyco(psyco):
    psyco.bind(DebTagLoader.load)
    psyco.bind(DebTagLoader.search)
    psyco.bind(DebTagFileLoader.getSections)
    psyco.bind(DebDirLoader.getSections)

hooks.register("enable-psyco", enablePsyco)

# vim:ts=4:sw=4:et

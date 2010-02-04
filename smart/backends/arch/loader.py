#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Cody Lee <platinummonkey@archlinux.us>
# and Anders F Bjorklund <afb@users.sourceforge.net>
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
from smart.channel import FileChannel
from smart.backends.arch.base import *
from smart.const import BLOCKSIZE
from smart import *
import os
import re
import posixpath
import tarfile
import tempfile

NAMERE = re.compile("^(.+)-([^-]+-[^-]+)$")

SECTIONRE = re.compile("^%([A-Z0-9]+)%$")

DEPENDSRE = re.compile("([\w.+-]+)([<=>]+)?([\w.+-]+)?")

class ArchPackageInfo(PackageInfo):

    def __init__(self, package, loader, info):
        PackageInfo.__init__(self, package)
        self._loader = loader
        self._info = info

    def getGroup(self):
        return self._info.get("groups", "Archlinux")

    def getSummary(self):
        return self._info.get("desc", "")

    def getDescription(self):
        return ""

    def getLicense(self):
        return self._info.get("license", "")

    def getURLs(self):
        info = self._info
        if "filename" in info and "baseurl" in info:
            pkg = self._package
            return [os.path.join(info["baseurl"], info["filename"])]
        return []

    def getSize(self, url):
        size = self._info.get("csize")
        if size:
            return long(size)
        return None

    def getMD5(self, url):
        return self._info.get("md5sum", None)

    def getBuildTime(self):
        date = self._info.get("builddate")
        if date:
            return int(date)
        return None

    def getInstalledSize(self):
        size = self._info.get("isize")
        if size:
            return long(size)
        return None

    def getReferenceURLs(self):
        info = self._info
        if "url" in info:
            return [info["url"]]
        return []

    def getPathList(self):
        self._paths = self._loader.getPaths(self)
        return self._paths.keys()

    def pathIsDir(self, path):
        return self._paths[path] == "d"

    def pathIsFile(self, path):
        return self._paths[path] == "f"

def parseFilePackageInfo(filename):
    infolst = []
    info = None
    desctag = None
    desctaglen = None
    tempname = None
    if filename.endswith(".tar.xz"):
        (output, tempname) = tempfile.mkstemp(".tar")
        try:
            import lzma
            input = lzma.LZMAFile(filename)
            data = input.read(BLOCKSIZE)
            while data:
                os.write(output, data)
                data = input.read(BLOCKSIZE)
            os.close(output)
        except ImportError, e:
            import commands
            if not os.path.exists(filename):
                raise IOError("File not found: '%s'" % filename)
            else:
                filename = os.path.abspath(filename)
            (status, output) = commands.getstatusoutput(
                               "unxz <'%s' >%s" % (filename, tempname))
            if (status != 0):
                raise Error, "%s, unxz helper could not be found" % e
        tar = tarfile.open(tempname)
    else:
        tar = tarfile.open(filename)
    file = tar.extractfile('.PKGINFO')
    for line in file.readlines():
        if line.startswith("pkgname"):
            name = line[9:].strip()
            if info:
                infolst.append(info)
            info = {}
            info["name"] = name
            desctag = None
        elif info:
            if line.startswith("pkgver"):
                info["version"] = line[8:].strip()
            elif line.startswith("pkgdesc"):
                info["desc"] = line[9:].strip()
            elif line.startswith("url"):
                info["url"] = line[6:].strip()
            elif line.startswith("builddate"):
                info["builddate"] = line[12:].strip()
            elif line.startswith("packager"):
                info["packager"]  = line[11:].strip()
            elif line.startswith("size"):
                info["isize"] = line[7:].strip()
            elif line.startswith("arch"):
                info["arch"] = line[7:].strip()
            elif line.startswith("license"):
                info["license"] = line[10:].strip()
            elif line.startswith("group"):
                info["groups"] = line[8:].strip()
            elif line.startswith("depend"):
                info["depends"] = line[9:].strip()
    if info:
        infolst.append(info)
    if tempname:
        os.unlink(tempname)
    file.close()
    return infolst

def parseFilePackageList(filename):
    filelist = {}
    if tarfile.is_tarfile(filename):
        tar = tarfile.open(filename)
        for info in tar.getmembers():
            file = info.name
            if file != '.PKGINFO':
                if file.endswith('/'):
                    file = file[:-1]
                filelist[file] = info.isdir() and "d" or "f"
    else:
        file = open(filename)
        if file:
            info = {}
            for line in file:
                if not line or not line.strip():
                    continue
                m = SECTIONRE.match(line)
                if m:
                    section = m.group(1).lower()
                    continue
                if section and section in info:
                    info[section].append(line.rstrip())
                else:
                    info[section] = [line.rstrip()]
            file.close()
        if info["files"]:
            for file in info["files"]:
                filelist[file] = file.endswith('/') and "d" or "f"
    return filelist

def parseDBPackageInfo(dirname):
    infolst = []
    info = {}
    for entry in os.listdir(dirname):
        if entry.endswith("desc") or entry.endswith("depends"):
            path = posixpath.join(dirname, entry)
            file = open(path)
            section = None
            for line in file:
                if not line or not line.strip():
                    continue
                m = SECTIONRE.match(line)
                if m:
                    section = m.group(1).lower()
                    continue
                if section and section in info:
                    info[section] = info[section] + "\n" + line.rstrip()
                else:
                    info[section] = line.rstrip()
            file.close()
    if info:
         infolst.append(info)
    return infolst

def parseSitePackageInfo(dbpath):
    infolst = {}
    info = None
    tempdir = tempfile.mkdtemp()
    pkgdir = None
    tar = tarfile.open(dbpath)
    for member in tar.getmembers():
        if member.isdir():
            if pkgdir:
                temppath = posixpath.join(tempdir, pkgdir)
                os.rmdir(temppath)
                pkgdir = None
            if info and name:
                infolst[name] = info
            name = member.name.rstrip("/")
            m = NAMERE.match(name)
            if not m:
                iface.error(_("Invalid package name: %s") % name)
                continue
            info = {}
        if member.name.endswith("desc") or member.name.endswith("depends"):
            pkgdir = name
            tar.extract(member, tempdir)
            temppath = posixpath.join(tempdir, member.name)
            file = open(temppath)
            section = None
            for line in file:
                if not line or not line.strip():
                    continue
                m = SECTIONRE.match(line)
                if m:
                    section = m.group(1).lower()
                    continue
                if section and section in info:
                    info[section] = info[section] + "\n" + line.rstrip()
                else:
                    info[section] = line.rstrip()
            file.close()
            os.unlink(temppath)
    if info and name:
         infolst[name] = info
    if pkgdir:
         temppath = posixpath.join(tempdir, pkgdir)
         os.rmdir(temppath)
         pkgdir = None
    return infolst.values()

def parseSitePackageList(flpath, dirname):
    info = None
    tempdir = tempfile.mkdtemp()
    pkgdir = None
    filelist = {}
    if flpath:
        pkgdir = None
        files = tarfile.open(flpath)
        #for member in files.getmembers():
        member = files.getmember("%s/files" % dirname)
        if member:
            name = dirname
            info = {}
            if member.isdir():
                if pkgdir:
                    temppath = posixpath.join(tempdir, pkgdir)
                    os.rmdir(temppath)
                    pkgdir = None
                name = member.name.rstrip("/")
            #if info and name and member.name.endswith("files"):
            if True:
                pkgdir = name
                files.extract(member, tempdir)
                temppath = posixpath.join(tempdir, member.name)
                file = open(temppath)
                section = None
                for line in file:
                    if not line or not line.strip():
                        continue
                    m = SECTIONRE.match(line)
                    if m:
                        section = m.group(1).lower()
                        continue
                    if section and section in info:
                        info[section].append(line.rstrip())
                    else:
                        info[section] = [line.rstrip()]
                file.close()
                os.unlink(temppath)
            if info["files"]:
                for file in info["files"]:
                    filelist[file] = file.endswith('/') and "d" or "f"
    if pkgdir:
         temppath = posixpath.join(tempdir, pkgdir)
         os.rmdir(temppath)
         pkgdir = None
    return filelist

class ArchLoader(Loader):

    def __init__(self, baseurl=None):
        Loader.__init__(self)
        self._baseurl = baseurl

    def getInfoList(self):
        return []

    def load(self):

        prog = iface.getProgress(self._cache)

        for info in self.getInfoList():

            name = info["name"]
            version = info["version"]
            if "arch" in info:
                version += "-" + info["arch"]

            prvargs = [(ArchProvides, name, version)]
            upgargs = [(ArchUpgrades, name, "<", version)]

            def parserelation(str):
                m = DEPENDSRE.match(str.strip())
                if m:
                    return m.group(1), m.group(2), m.group(3)
                else:
                    return str.strip(), None, None

            def parserelations(str):
                ret = []
                for descr in str.strip().splitlines():
                    ret.append(parserelation(descr))
                return ret

            if "provides" in info:
                for prv in parserelations(info["provides"]):
                    n, r, v = prv
                    prvargs.append((ArchProvides, n, v))

            reqargs = []
            if "depends" in info:
                for req in parserelations(info["depends"]):
                    n, r, v = req
                    reqargs.append((ArchRequires, n, r, v))

            cnfargs = []
            if "conflicts" in info:
                for cnf in parserelations(info["conflicts"]):
                    n, r, v = cnf
                    cnfargs.append((ArchConflicts, n, r, v))


            pkg = self.buildPackage((ArchPackage, name, version),
                                    prvargs, reqargs, upgargs, cnfargs)

            if self._baseurl:
                info["baseurl"] = self._baseurl
            
            pkg.loaders[self] = info

            prog.add(1)
            prog.show()

    def getInfo(self, pkg):
        return ArchPackageInfo(pkg, self, pkg.loaders[self])

    def getPaths(self, info):
        return {}

class ArchDirLoader(ArchLoader):

    def __init__(self, dir, filename=None):
        self._dir = os.path.abspath(dir)
        ArchLoader.__init__(self, "file:///" + self._dir)
        if filename:
            self._filenames = [filename]
        else:
            self._filenames = [x for x in os.listdir(dir)
                                  if x.endswith(".pkg.tar.gz") \
                                  or x.endswith(".pkg.tar.xz")]

    def getInfoList(self):
        for filename in self._filenames:
            filepath = os.path.join(self._dir, filename)
            infolst = parseFilePackageInfo(filepath)
            if infolst:
                info = infolst[0]
                info["filename"] = filename
                info["csize"] = os.path.getsize(filepath)
                yield info

    def getLoadSteps(self):
        return len(self._filenames)

    def getPaths(self, info):
        return parseFilePackageList(os.path.join(self._dir, info._info["filename"]))

class ArchDBLoader(ArchLoader):

    def __init__(self, dir=None):
        ArchLoader.__init__(self)
        if dir is None:
            dir = os.path.join(sysconf.get("arch-root", "/"),
                               sysconf.get("arch-packages-dir",
                                           "var/lib/pacman"),
                               "local")
        self._dir = dir
        self.setInstalled(True)
    
    def getInfoList(self):
        for entry in os.listdir(self._dir):
            infolst = parseDBPackageInfo(os.path.join(self._dir, entry))
            if infolst:
                info = infolst[0]
                info["filename"] = None
                yield info

    def getLoadSteps(self):
        return len(os.listdir(self._dir))

    def getPaths(self, info):
        dirname = "%s-%s" % (info._info["name"], info._info["version"])
        return parseFilePackageList(os.path.join(self._dir, dirname, "files"))

class ArchSiteLoader(ArchLoader):

    def __init__(self, filename, pathlist, baseurl):
        ArchLoader.__init__(self)
        self._filename = filename
        self._pathlist = pathlist
        self._baseurl = baseurl
    
    def getInfoList(self):
        return parseSitePackageInfo(self._filename)

    def getLoadSteps(self):
        file = tarfile.open(self._filename)
        total = 0
        for info in file.getmembers():
            if info.isdir():
                total += 1
        file.close()
        return total

    def getPaths(self, info):
        dirname = "%s-%s" % (info._info["name"], info._info["version"])
        return parseSitePackageList(self._pathlist, dirname)

class ArchFileChannel(FileChannel):

    def fetch(self, fetcher, progress):
        digest = os.path.getmtime(self._filename)
        if digest == self._digest:
            return True
        self.removeLoaders()
        dirname, basename = os.path.split(self._filename)
        loader = ArchDirLoader(dirname, basename)
        loader.setChannel(self)
        self._loaders.append(loader)
        self._digest = digest
        return True

def createFileChannel(filename):
    if filename.endswith(".pkg.tar.gz") or filename.endswith(".pkg.tar.xz"):
        return ArchFileChannel(filename)
    return None

hooks.register("create-file-channel", createFileChannel)

def enablePsyco(psyco):
    psyco.bind(parsePackageInfo)
    psyco.bind(ArchLoader.load)
    psyco.bind(ArchDBLoader.getInfoList)

hooks.register("enable-psyco", enablePsyco)

# vim:ts=4:sw=4:et

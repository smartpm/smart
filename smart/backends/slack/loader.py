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
from smart.cache import Loader, PackageInfo
from smart.channel import FileChannel
from smart.backends.slack.base import *
from smart.const import BLOCKSIZE
from smart import *
import os
import re
import posixpath
import tarfile
import tempfile

NAMERE = re.compile("^(.+?)-([^-]+-[^-]+-[^-]+?)(.t[gblx]z)?$")

class SlackPackageInfo(PackageInfo):

    def __init__(self, package, info):
        PackageInfo.__init__(self, package)
        self._info = info

    def getGroup(self):
        return self._info.get("group", "Slackware")

    def getLicense(self):
        return self._info.get("license", "Unknown")

    def getSummary(self):
        return self._info.get("summary", "")

    def getDescription(self):
        return self._info.get("description", "")

    def getReferenceURLs(self):
        website = self._info.get("website", "")
        if website:
            return [website]
        return []

    def getURLs(self):
        info = self._info
        if "location" in info and "baseurl" in info:
            pkg = self._package
            version = info.get("version", pkg.version)
            type = info.get("type", ".tgz")
            baseurl = info["baseurl"]
            location = info["location"]
            if baseurl.endswith('/'):
                baseurl = baseurl[:-1]
            if location.startswith("./"):
                location = location[2:]
            def mergepath(begin, end):
                begin = begin.split('/')
                end = end.split('/')
                # strip end from begin
                for dir in reversed(end):
                    if dir == begin[-1]:
                        begin = begin[:-1]
                begin = '/'.join(begin)            
                end = '/'.join(end)            
                return posixpath.join(begin, end)
            return [os.path.join(mergepath(baseurl, location),
                   "%s-%s%s" % (pkg.name, version, type))]
        return []

    def getMD5(self, url):
        return self._info.get("md5", None)

    def getPathList(self):
        return self._info.get("filelist", [])

def parsePackageFile(filename):
    infolst = []
    info = {}
    dirname, basename = os.path.split(filename)
    package, type = os.path.splitext(basename)
    name, version = package.split('-', 1)
    info["name"] = name
    info["version"] = version
    info["type"] = type
    if type == ".txz":
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
    file = tar.extractfile('install/slack-desc')
    if file:
        desctag = "%s:" % info["name"]
        desctaglen = len(desctag)
        for line in file.readlines():
            if desctag and line.startswith(desctag):
                line = line[desctaglen:].strip()
                if "summary" not in info:
                    info["summary"] = line
                elif "description" not in info:
                    if line:
                        info["description"] = line
                else:
                    if line.startswith("License: "):
                        info["license"] = line[9:]
                    if line.startswith("Website: "):
                        info["website"] = line[9:]
                    info["description"] += "\n"
                    info["description"] += line
    for member in tar.getmembers():
        file = member.name
        if file.endswith('/'):
            file = file[:-1]
        if file != "./" and not file.startswith("install"):
            if "filelist" in info:
                info["filelist"].append(file)
            else:
                info["filelist"] = [file]
    if info:
        infolst.append(info)
    return infolst

def parsePackageInfo(filename, checksum=None):
    md5sums = {}
    infolst = []
    info = None
    desctag = None
    desctaglen = None
    filelist = False
    if checksum:
        file = open(checksum)
        for line in file:
            if line.find(" ./") == -1:
                continue
            (md5, path) = line.strip().split(None, 1)
            md5sums[path] = md5
        file.close()
    file = open(filename)
    for line in file:
        if line.startswith("PACKAGE NAME:"):
            name = line[13:].strip()
            m = NAMERE.match(name)
            if not m:
                iface.warning(_("Invalid package name: %s") % name)
                continue
            if info:
                infolst.append(info)
            info = {}
            if m.lastindex < 3:
                info["name"], info["version"], ignore = m.groups()
            else:
                info["name"], info["version"], info["type"] = m.groups()
            desctag = None
            filelist = False
        elif info:
            if line.startswith("PACKAGE LOCATION:"):
                location = line[17:].strip()
                info["location"] = location
                if location.startswith("./"):
                    location = location[2:]
                path = "%s/%s" % (location, name)
                if path in md5sums:
                     info["md5"] = md5sums[path]
                if location.endswith(".tbz"):
                    info["type"] = ".tbz"
                if location.endswith(".tlz"):
                    info["type"] = ".tlz"
                if location.endswith(".txz"):
                    info["type"] = ".txz"
            elif line.startswith("PACKAGE REQUIRED:"):
                required = line[17:].strip()
                info["required"] = required
            elif line.startswith("PACKAGE CONFLICTS:"):
                conflicts = line[18:].strip()
                info["conflicts"] = conflicts
            elif line.startswith("PACKAGE DESCRIPTION:"):
                desctag = "%s:" % info["name"]
                desctaglen = len(desctag)
            elif line.startswith("FILE LIST:"):
                filelist = True
            elif filelist:
                line = line.rstrip()
                if line != "./":
                    line = "/"+line
                    if "filelist" in info:
                        info["filelist"].append(line)
                    else:
                        info["filelist"] = [line]
            elif desctag and line.startswith(desctag):
                line = line[desctaglen:].strip()
                if "summary" not in info:
                    info["summary"] = line
                elif "description" not in info:
                    if line:
                        info["description"] = line
                else:
                    if line.startswith("License: "):
                        info["license"] = line[9:]
                    if line.startswith("Website: "):
                        info["website"] = line[9:]
                    info["description"] += "\n"
                    info["description"] += line
    if info:
        infolst.append(info)
    file.close()
    return infolst

class SlackLoader(Loader):

    def __init__(self, baseurl=None):
        Loader.__init__(self)
        self._md5sums = {}
        self._baseurl = baseurl

    def getInfoList(self):
        return []

    def load(self):

        prog = iface.getProgress(self._cache)

        for info in self.getInfoList():

            name = info["name"]
            version = info["version"]
            
            prvargs = [(SlackProvides, name, version)]
            upgargs = [(SlackUpgrades, name, "<", version)]

            def parserelation(str):
                toks = str.strip().split(" ")
                if len(toks) == 3:
                    return toks[0], toks[1], toks[2]
                else:
                    return str.strip(), None, None

            def parserelations(str):
                if not str:
                    return []
                ret = []
                for descr in str.strip().split(","):
                    group = descr.split("|")
                    if len(group) == 1:
                       ret.append(parserelation(group[0]))
                    else:
                       ret.append([parserelation(x) for x in group])
                return ret

            reqargs = []
            if "required" in info:
                for req in parserelations(info["required"]):
                    if type(req) is not list:
                        n, r, v = req
                        reqargs.append((SlackRequires, n, r, v))
                    else:
                        reqargs.append((SlackOrRequires, tuple(req)))

            cnfargs = []
            if "conflicts" in info:
                for cnf in parserelations(info["conflicts"]):
                    n, r, v = cnf
                    cnfargs.append((SlackConflicts, n, r, v))

            pkg = self.buildPackage((SlackPackage, name, version),
                                    prvargs, reqargs, upgargs, cnfargs)

            if self._baseurl:
                info["baseurl"] = self._baseurl
            
            pkg.loaders[self] = info

            prog.add(1)
            prog.show()

    def getInfo(self, pkg):
        return SlackPackageInfo(pkg, pkg.loaders[self])

class SlackDirLoader(SlackLoader):

    def __init__(self, dir, filename=None):
        self._dir = os.path.abspath(dir)
        SlackLoader.__init__(self, "file://" + self._dir)
        if filename:
            self._filenames = [filename]
        else:
            self._filenames = [x for x in os.listdir(dir)
                                      if x.endswith(".tgz") \
                                      or x.endswith(".tbz") \
                                      or x.endswith(".tlz") \
                                      or x.endswith(".txz")]

    def getInfoList(self):
        for filename in self._filenames:
            filepath = os.path.join(self._dir, filename)
            infolst = parsePackageFile(filepath)
            if infolst:
                info = infolst[0]
                info["location"] = self._dir.lstrip('/')
                yield info

    def getLoadSteps(self):
        return len(self._filenames)

class SlackDBLoader(SlackLoader):

    def __init__(self, dir=None):
        SlackLoader.__init__(self)
        if dir is None:
            dir = os.path.join(sysconf.get("slack-root", "/"),
                               sysconf.get("slack-packages-dir",
                                           "/var/log/packages"))
        self._dir = dir
        self.setInstalled(True)
    
    def getInfoList(self):
        for entry in os.listdir(self._dir):
            infolst = parsePackageInfo(os.path.join(self._dir, entry))
            if infolst:
                info = infolst[0]
                info["location"] = None
                yield info

    def getLoadSteps(self):
        return len(os.listdir(self._dir))

class SlackSiteLoader(SlackLoader):

    def __init__(self, filename, checksum, baseurl):
        SlackLoader.__init__(self)
        self._filename = filename
        self._checksum = checksum
        self._baseurl = baseurl
    
    def getInfoList(self):
        return parsePackageInfo(self._filename, self._checksum)

    def getLoadSteps(self):
        file = open(self._filename)
        total = 0
        for line in file:
            if line.startswith("PACKAGE NAME:"):
                total += 1
        file.close()
        return total

class SlackFileChannel(FileChannel):

    def fetch(self, fetcher, progress):
        digest = os.path.getmtime(self._filename)
        if digest == self._digest:
            return True
        self.removeLoaders()
        dirname, basename = os.path.split(self._filename)
        loader = SlackDirLoader(dirname, basename)
        loader.setChannel(self)
        self._loaders.append(loader)
        self._digest = digest
        return True

def createFileChannel(filename):
    if filename.endswith(".tgz") \
    or filename.endswith(".tbz") \
    or filename.endswith(".tlz") \
    or filename.endswith(".txz"):
        return SlackFileChannel(filename)
    return None

hooks.register("create-file-channel", createFileChannel)

def enablePsyco(psyco):
    psyco.bind(parsePackageFile)
    psyco.bind(parsePackageInfo)
    psyco.bind(SlackLoader.load)
    psyco.bind(SlackDBLoader.getInfoList)

hooks.register("enable-psyco", enablePsyco)

# vim:ts=4:sw=4:et

#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# Archlinux module written by Cody Lee (aka. platinummonkey) <platinummonkey@archlinux.us>
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
from smart.backends.arch.base import *
from smart import *
import os,  re,  tarfile

nameRE = re.compile("^(.+)-([^-]+-[^-]+-[^-.]+)(?:.pkg.tar.gz)?$")

class ArchPackageInfo(PackageInfo):

    def __init__(self, package, info):
        PackageInfo.__init__(self, package)
        self._info = info

    def getGroup(self):
        return "Archlinux"

    def getSummary(self):
        return self._info.get("summary", "")

    def getDescription(self):
        return self._info.get("description", "")

    def getURLs(self):
        info = self._info
        if "location" in info and "baseurl" in info:
            pkg = self._package
            return [os.path.join(info["baseurl"], info["location"],
                                 "%s-%s.pkg.tar.gz" % (pkg.name, pkg.version))]
        return []

    def getPathList(self):
        return self._info.get("filelist", [])

def parseDBPackageInfo(filename):
    infolst = []
    info = None
    desctag = None
    desctaglen = None
    filelist = False
    #file = open(filename)
    tar = tarfile.open(filename)
    file = tar.extractfile('.PKGINFO')
    for line in file:
        if line.startswith("pkgname"):
            name = line[9:].strip()
            #m = namere.match(name)
            #if not m:
            #    iface.warning(_("Invalid package name: %s") % name)
            #    continue
            if info:
                infolst.append(info)
            info = {}
            info["name"] = name #, info["version"] = m.groups()
            desctag = None
            filelist = False
        elif info:
            if line.startswith("pkgver"):
                info["version"] = line[8:].strip()
            elif line.startswith("pkgdesc"):
                info["description"] = line[9:].strip()
            elif line.startswith("url"):
                info["url"] = line[6:].strip()
            elif line.startswith("builddate"):
                info["builddate"] = line[12:].strip()
            elif line.startswith("packager"):
                info["packager"]  = line[11:].strip()
            elif line.startswith("size"):
                info["size"] = line[7:].strip()
            elif line.startswith("arch"):
                info["arch"] = line[7:].strip()
            elif line.startswith("license"):
                info["license"] = line[10:].strip()
            elif line.startswith("group"):
                info["group"] = line[8:].strip()
            elif line.startswith("depend"):
                info["depend"] = line[9:].strip()
            elif filelist:
                line = line.rstrip()
                if line != "./":
                    line = "/"+line
                    if "filelist" in info:
                        info["filelist"].append(line)
                    else:
                        info["filelist"] = [line]
            ################################
    if info:
        infolst.append(info)
    file.close()
    return infolst

def parseSitePackageInfo(desclist, dependlist):
    # Open on *.db.tar.gz file and create a desclist and dependlist for each pkg
    tar = tarfile.open
    file_list = tar.getnames()
    file_list_its = file_list / 3 # pkg dir > (desc, depends) --- 3 'files/names' per pkg
    i, file_dict = 0, {}
    # parse through desc file
    while i < len(desclist):
        if re.match("\%*\%",desclist[i]): # match definitions in file (ex. "%VERSION%" in human readable)
            ftitle = desclist[i].lstrip('%').rstrip('%\n')
            i+=1; finfo = ""
            while desclist[i] != '\n':
                finfo = finfo + desclist[i]
                i+=1
            i+=1
            file_dict[ftitle] = finfo
        else:
            raise "iteration error at iteration %d in desclist" % i
    # parse through depends file
    i = 0
    while i < len(dependlist):
        if re.match("\%*\%",dependlist[i]): # match definitions in file (ex. "%DEPENDS%" in human readable)
            ftitle = dependlist[i].lstrip('%').rstrip('%\n')
            i+=1; finfo = ""
            while dependlist[i] != '\n':
                finfo = finfo + dependlist[i]
                i+=1
            i+=1
            file_dict[ftitle] = finfo
        else:
            raise "iteration error at iteration %d in dependlist" % i
    return file_dict
    
class ArchLoader(Loader):

    def __init__(self):
        Loader.__init__(self)
        self._baseurl = None

    def getInfoList(self):
        return []

    def load(self):

        reqargs = cnfargs = []

        prog = iface.getProgress(self._cache)

        for info in self.getInfoList():

            name = info["name"]
            version = info["version"]

            prvargs = [(ArchProvides, name, version)]
            upgargs = [(ArchUpgrades, name, "<", version)]

            pkg = self.buildPackage((ArchPackage, name, version),
                                    prvargs, reqargs, upgargs, cnfargs)

            if self._baseurl:
                info["baseurl"] = self._baseurl
            
            pkg.loaders[self] = info

            prog.add(1)
            prog.show()

    def getInfo(self, pkg):
        return ArchPackageInfo(pkg, pkg.loaders[self])

class ArchDBLoader(ArchLoader):

    def __init__(self, dir=None):
        ArchLoader.__init__(self)
        if dir is None:
            dir = os.path.join(sysconf.get("Arch-root", "/"),
                               sysconf.get("Arch-packages-dir",
                                           "/var/cache/pacman/pkg"))
        self._dir = dir
        self.setInstalled(True)
    
    def getInfoList(self):
        for entry in os.listdir(self._dir):
            infolst = parseDBPackageInfo(os.path.join(self._dir, entry))
            if infolst:
                info = infolst[0]
                info["location"] = None
                yield info

    def getLoadSteps(self):
        return len(os.listdir(self._dir))

class ArchSiteLoader(ArchLoader):

    def __init__(self, filename, baseurl):
        ArchLoader.__init__(self)
        self._filename = filename
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

def enablePsyco(psyco):
    psyco.bind(parsePackageInfo)
    psyco.bind(ArchLoader.load)
    psyco.bind(ArchDBLoader.getInfoList)

hooks.register("enable-psyco", enablePsyco)

# vim:ts=4:sw=4:et

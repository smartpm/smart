from cpm.cache import Loader, PackageInfo
from cpm.backends.slack import *
from cpm import *
import os
import re

NAMERE = re.compile("^(.+)-([^-]+-[^-]+-[^-.]+)(?:.tgz)?$")

class SlackPackageInfo(PackageInfo):

    def __init__(self, package, info):
        PackageInfo.__init__(self, package)
        self._info = info

    def getGroup(self):
        return "Slackware"

    def getSummary(self):
        return self._info.get("summary")

    def getDescription(self):
        return self._info.get("description")

    def getURL(self):
        info = self._info
        if "location" in info and "baseurl" in info:
            pkg = self._package
            return os.path.join(info["baseurl"], info["location"],
                                "%s-%s.tgz" % (pkg.name, pkg.version))

    def getPathList(self):
        return self._info.get("filelist", [])

def parsePackageInfo(filename):
    infolst = []
    info = None
    desctag = None
    desctaglen = None
    filelist = False
    file = open(filename)
    for line in file:
        if line.startswith("PACKAGE NAME:"):
            name = line[13:].strip()
            m = NAMERE.match(name)
            if not m:
                iface.warning("Invalid package name: %s" % name)
                continue
            if info:
                infolst.append(info)
            info = {}
            info["name"], info["version"] = m.groups()
            desctag = None
            filelist = False
        elif info:
            if line.startswith("PACKAGE LOCATION:"):
                location = line[17:].strip()
                if location.startswith("./"):
                    location = location[2:]
                info["location"] = location
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
                    info["description"] += "\n"
                    info["description"] += line
    if info:
        infolst.append(info)
    file.close()
    return infolst

class SlackLoader(Loader):

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

            prvargs = [(SlackProvides, name, version)]
            upgargs = [(SlackUpgrades, name, "<", version)]

            pkg = self.newPackage((SlackPackage, name, version),
                                  prvargs, reqargs, upgargs, cnfargs)

            if self._baseurl:
                info["baseurl"] = self._baseurl
            
            pkg.loaders[self] = info

            prog.add(1)
            prog.show()

    def getInfo(self, pkg):
        return SlackPackageInfo(pkg, pkg.loaders[self])

class SlackDBLoader(SlackLoader):

    def __init__(self, dir=None):
        SlackLoader.__init__(self)
        if dir is None:
            dir = sysconf.get("slack-packages-dir", "/var/log/packages")
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

    def __init__(self, filename, baseurl):
        SlackLoader.__init__(self)
        self._filename = filename
        self._baseurl = baseurl
    
    def getInfoList(self):
        return parsePackageInfo(self._filename)

    def getLoadSteps(self):
        file = open(self._filename)
        total = 0
        for line in file:
            if line.startswith("PACKAGE NAME:"):
                total += 1
        file.close()
        return total

# vim:ts=4:sw=4:et

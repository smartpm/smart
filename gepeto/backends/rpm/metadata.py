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
from gepeto.cache import PackageInfo, Loader
from gepeto.backends.rpm import *
from gepeto import *
import posixpath
import locale
import rpm
import os

from xml.parsers import expat

NS_COMMON = "http://linux.duke.edu/metadata/common"
NS_RPM    = "http://linux.duke.edu/metadata/rpm"

class RPMMetaDataPackageInfo(PackageInfo):

    def __init__(self, package, info):
        PackageInfo.__init__(self, package)
        self._info = info

    def getURLs(self):
        url = self._info.get("location")
        if url:
            return [url]
        return []

    def getSize(self, url):
        return self._info.get("size")

    def getMD5(self, url):
        return self._info.get("md5")

    def getSHA(self, url):
        return self._info.get("sha")

    def getDescription(self):
        return self._info.get("description", "")

    def getSummary(self):
        return self._info.get("summary", "")

    def getGroup(self):
        return self._info.get("group", "")


class RPMMetaDataLoader(Loader):
 
    COMPMAP = { "EQ":"=", "LT":"<", "LE":"<=", "GT":">", "GE":">="}

    def __init__(self, filename, baseurl):
        Loader.__init__(self)
        self._filename = filename
        self._baseurl = baseurl

        self._queue = []
        self._data = None

        self._fileprovides = {}

        self._name = None
        self._version = None
        self._arch = None

        self._reqdict = {}
        self._prvdict = {}
        self._upgdict = {}
        self._cnfdict = {}
        self._filedict = {}

        self._info = {}

        self._skip = None

        self._starthandler = {}
        self._endhandler = {}

        for ns, attr in ((NS_COMMON, "MetaData"),
                         (NS_COMMON, "Package"),
                         (NS_COMMON, "Name"),
                         (NS_COMMON, "Arch"),
                         (NS_COMMON, "Version"),
                         (NS_COMMON, "Summary"),
                         (NS_COMMON, "Description"),
                         (NS_COMMON, "Size"),
                         (NS_COMMON, "Location"),
                         (NS_COMMON, "Format"),
                         (NS_COMMON, "Group"),
                         (NS_COMMON, "CheckSum"),
                         (NS_RPM, "Entry"),
                         (NS_RPM, "Requires"),
                         (NS_RPM, "Provides"),
                         (NS_RPM, "Conflicts"),
                         (NS_RPM, "Obsoletes")):
            handlername = "_handle%sStart" % attr
            handler = getattr(self, handlername, None)
            nsattr = "%s %s" % (ns, attr.lower())
            if handler:
                self._starthandler[nsattr] = handler
            handlername = "_handle%sEnd" % attr
            handler = getattr(self, handlername, None)
            if handler:
                self._endhandler[nsattr] = handler
            setattr(self, attr.upper(), nsattr)

    def reset(self):
        Loader.reset(self)
        del self._queue[:]
        self._resetPackage()
        self._fileprovides.clear()

    def _resetPackage(self):
        self._data = None
        self._name = None
        self._version = None
        self._arch = None
        self._reqdict.clear()
        self._prvdict.clear()
        self._upgdict.clear()
        self._cnfdict.clear()
        self._filedict.clear()
        self._info = {}

    def _startElement(self, name, attrs):
        if self._skip:
            return
        handler = self._starthandler.get(name)
        if handler:
            handler(name, attrs)
        self._data = None
        self._queue.append((name, attrs))

    def _endElement(self, name):
        if self._skip:
            if name == self._skip:
                self._skip = None
                _name = None
                while _name != name:
                    _name, attrs = self._queue.pop()
            return
        _name, attrs = self._queue.pop()
        assert _name == name
        handler = self._endhandler.get(name)
        if handler:
            handler(name, attrs, self._data)
        self._data = None

    def _charData(self, data):
        self._data = data

    def _handleArchEnd(self, name, attrs, data):
        if rpm.archscore(data) == 0:
            self._skip = self.PACKAGE
        else:
            self._arch = data

    def _handleNameEnd(self, name, attrs, data):
        self._name = data

    def _handleVersionEnd(self, name, attrs, data):
        e = attrs.get("epoch")
        if e:
            self._version = "%s:%s-%s" % (e, attrs.get("ver"), attrs.get("rel"))
        else:
            self._version = "%s-%s" % (attrs.get("ver"), attrs.get("rel"))

    def _handleSummaryEnd(self, name, attrs, data):
        self._info["summary"] = data

    def _handleDescriptionEnd(self, name, attrs, data):
        self._info["description"] = data

    def _handleSizeEnd(self, name, attrs, data):
        self._info["size"] = int(attrs.get("package"))
        self._info["installed_size"] = int(attrs.get("installed"))

    def _handleCheckSumEnd(self, name, attrs, data):
        self._info[attrs.get("type")] = data

    def _handleLocationEnd(self, name, attrs, data):
        self._info["location"] = posixpath.join(self._baseurl,
                                                attrs.get("href"))

    def _handleGroupEnd(self, name, attrs, data):
        self._info["group"] = data

    def _handleEntryEnd(self, name, attrs, data):
        name = attrs.get("name")
        if not name or name[:7] in ("rpmlib(", "config("):
            return
        if "ver" in attrs:
            e = attrs.get("epoch")
            v = attrs.get("ver")
            r = attrs.get("rel")
            version = v
            if e:
                version = "%s:%s" % (e, version)
            if r:
                version = "%s-%s" % (version, r)
            if "flags" in attrs:
                relation = self.COMPMAP.get(attrs.get("flags"))
            else:
                relation = None
        else:
            version = None
            relation = None
        lastname = self._queue[-1][0]
        if lastname == self.REQUIRES:
            self._reqdict[(RPMRequires, name, relation, version)] = True
        elif lastname == self.PROVIDES:
            if name[0] == "/":
                self._filedict[name] = True
            else:
                if name == self._name and version == self._version:
                    version = "%s.%s" % (version, self._arch)
                    Prv = RPMNameProvides
                else:
                    Prv = RPMProvides
                self._prvdict[(Prv, name, version)] = True
        elif lastname == self.OBSOLETES:
            tup = (RPMObsoletes, name, relation, version)
            self._upgdict[tup] = True
            self._cnfdict[tup] = True
        elif lastname == self.CONFLICTS:
            self._cnfdict[(RPMConflicts, name, relation, version)] = True

    def _handleFileEnd(self, name, attrs, data):
        if lastname == self.PROVIDES:
            self._prvdict[(RPMProvides, data, None, None)]

    def _handlePackageStart(self, name, attrs):
        if attrs.get("type") != "rpm":
            self._skip = self.PACKAGE

    def _handlePackageEnd(self, name, attrs, data):
        name = self._name
        version = self._version
        versionarch = "%s.%s" % (version, self._arch)

        self._upgdict[(RPMObsoletes, name, '<', versionarch)] = True

        reqargs = [x for x in self._reqdict
                   if (RPMProvides, x[1], x[3]) not in self._prvdict]
        prvargs = self._prvdict.keys()
        cnfargs = self._cnfdict.keys()
        upgargs = self._upgdict.keys()

        pkg = self.buildPackage((RPMPackage, name, versionarch),
                                prvargs, reqargs, upgargs, cnfargs)
        pkg.loaders[self] = self._info

        self._fileprovides.setdefault(pkg, []).extend(self._filedict.keys())

        self._resetPackage()
        
    def load(self):
        self._progress = iface.getProgress(self._cache)

        parser = expat.ParserCreate(namespace_separator=" ")
        parser.StartElementHandler = self._startElement
        parser.EndElementHandler = self._endElement
        parser.CharacterDataHandler = self._charData
        parser.returns_unicode = False

        try:
            RPMPackage.ignoreprereq = True
            parser.ParseFile(open(self._filename))
        finally:
            RPMPackage.ignoreprereq = False

    def loadFileProvides(self, fndict):
        bfp = self.buildFileProvides
        for pkg in self._fileprovides:
            for fn in self._fileprovides[pkg]:
                if fn in fndict:
                    bfp(pkg, (RPMProvides, fn))

    def getInfo(self, pkg):
        return RPMMetaDataPackageInfo(pkg, pkg.loaders[self])

    def getLoadSteps(self):
        return 0

# vim:ts=4:sw=4:et

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
from smart.cache import PackageInfo, Loader
from smart.backends.rpm import *
from smart import *
import posixpath
import locale
import rpm
import os

from xml.parsers import expat

class RPMRedCarpetPackageInfo(PackageInfo):

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


class RPMRedCarpetLoader(Loader):
 
    def __init__(self, filename, baseurl):
        Loader.__init__(self)
        self._filename = filename
        self._baseurl = baseurl

        self._queue = []
        self._data = None

        self._fileprovides = {}

        self._name = None
        self._epoch = None
        self._version = None
        self._release = None
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

        for attr in ("Package", "Name", "Summary", "Description", "Arch",
                     "Section", "History", "Update", "Epoch", "Version",
                     "Release", "FileName", "FileSize", "Description",
                     "Requires", "Provides", "Conflicts", "Obsoletes", "Dep"):
            handlername = "_handle%sStart" % attr
            handler = getattr(self, handlername, None)
            lattr = attr.lower()
            if handler:
                self._starthandler[lattr] = handler
            handlername = "_handle%sEnd" % attr
            handler = getattr(self, handlername, None)
            if handler:
                self._endhandler[lattr] = handler
            setattr(self, attr.upper(), lattr)

    def reset(self):
        Loader.reset(self)
        del self._queue[:]
        self._resetPackage()
        self._fileprovides.clear()

    def _resetPackage(self):
        self._data = None
        self._name = None
        self._epoch = None
        self._version = None
        self._release = None
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
        self._data = ""
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
        self._data = ""

    def _charData(self, data):
        self._data += data

    def _handleNameEnd(self, name, attrs, data):
        self._name = data

    def _handleEpochEnd(self, name, attrs, data):
        self._epoch = data

    def _handleVersionEnd(self, name, attrs, data):
        self._version = data

    def _handleReleaseEnd(self, name, attrs, data):
        self._release = data

    def _handleArchEnd(self, name, attrs, data):
        if rpm.archscore(data) == 0:
            self._skip = self.PACKAGE
        else:
            self._arch = data

    def _handleSectionEnd(self, name, attrs, data):
        self._info["group"] = data

    def _handleSummaryEnd(self, name, attrs, data):
        self._info["summary"] = data

    def _handleDescriptionEnd(self, name, attrs, data):
        if self._queue[-1][0] == self.PACKAGE:
            self._info["description"] = data

    def _handleFileNameEnd(self, name, attrs, data):
        self._info["location"] = posixpath.join(self._baseurl, data)

    def _handleFileSizeEnd(self, name, attrs, data):
        self._info["size"] = int(data)

    def _handleUpdateEnd(self, name, attrs, data):
        self._skip = self.HISTORY

    def _handleDepEnd(self, name, attrs, data):
        name = attrs.get("name")
        if not name or name[:7] in ("rpmlib(", "config("):
            return
        if "version" in attrs:
            e = attrs.get("epoch")
            v = attrs.get("version")
            r = attrs.get("release")
            version = v
            if e:
                version = "%s:%s" % (e, version)
            if r:
                version = "%s-%s" % (version, r)
            relation = attrs.get("op")
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
                self._prvdict[(RPMProvides, name, version)] = True
        elif lastname == self.OBSOLETES:
            tup = (RPMObsoletes, name, relation, version)
            self._upgdict[tup] = True
            self._cnfdict[tup] = True
        elif lastname == self.CONFLICTS:
            self._cnfdict[(RPMConflicts, name, relation, version)] = True

    def _handlePackageEnd(self, name, attrs, data):
        name = self._name

        if self._epoch:
            version = "%s:%s-%s" % (self._epoch, self._version, self._release)
        else:
            version = "%s-%s" % (self._version, self._release)
        versionarch = "%s.%s" % (version, self._arch)

        self._upgdict[(RPMObsoletes, name, '<', versionarch)] = True

        reqargs = [x for x in self._reqdict
                   if (RPMProvides, x[1], x[3]) not in self._prvdict]
        prvargs = self._prvdict.keys()
        cnfargs = self._cnfdict.keys()
        upgargs = self._upgdict.keys()

        for i in range(len(prvargs)):
            tup = prvargs[i]
            if tup[1] == name and tup[2] == version:
                prvargs[i] = (RPMNameProvides, tup[1], versionarch)
                break

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
                    bfp(pkg, (RPMProvides, fn, None))

    def getInfo(self, pkg):
        return RPMRedCarpetPackageInfo(pkg, pkg.loaders[self])

    def getLoadSteps(self):
        return 0

# vim:ts=4:sw=4:et

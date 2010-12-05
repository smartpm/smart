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
from smart.backends.rpm.metadata import RPMMetaDataLoader
from smart.backends.rpm.updateinfo import RPMUpdateInfo
from smart.util.filetools import getFileDigest

try:
    from xml.etree import ElementTree
except ImportError:
    try:
        from elementtree import ElementTree
    except ImportError:
        from smart.util.elementtree import ElementTree

from smart.const import SUCCEEDED, FAILED, NEVER, ALWAYS
from smart.channel import PackageChannel, MirrorsChannel
from smart import *
import posixpath
import commands
import os

from xml.parsers import expat

NS = "{http://linux.duke.edu/metadata/repo}"
DATA = NS+"data"
LOCATION = NS+"location"
CHECKSUM = NS+"checksum"
OPENCHECKSUM = NS+"open-checksum"

ML = "{http://www.metalinker.org/}"
FILES = ML+"files"
FILE = ML+"file"
RESOURCES = ML+"resources"
URL = ML+"url"

class RPMMetaDataChannel(PackageChannel, MirrorsChannel):

    # It's important for the default to be here so that old pickled
    # instances which don't have these attributes still work fine.
    _mirrors = {}
    _mirrorlist = ""
    _fingerprint = None

    def __init__(self, baseurl, mirrorlist=None, fingerprint=None, *args):
        super(RPMMetaDataChannel, self).__init__(*args)
        self._baseurl = baseurl
        self._mirrorlist = mirrorlist
        if fingerprint:
            self._fingerprint = "".join(fingerprint.split())

    def getCacheCompareURLs(self):
        return [posixpath.join(self._baseurl, "repodata/repomd.xml")]

    def getFetchSteps(self):
        if self._fingerprint:
            return 5
        else:
            return 4

    def loadMetalink(self, metalinkfile):
        self._mirrors.clear()

        try:
            root = ElementTree.parse(metalinkfile).getroot()
        except (expat.error, SyntaxError), e: # ElementTree.ParseError
            iface.warning(_("Could not load meta link. Continuing with base URL only."))
            iface.debug(unicode(e))
            return

        filename = None
        for node in root.getiterator():
            if node.tag == FILE:
                filename = node.get("name")
                continue
            elif node.tag != RESOURCES:
                continue
            for subnode in node.getchildren():
                if subnode.tag != URL:
                    continue
                type = subnode.get("type")
                preference = subnode.get("preference")
                if type != "http" and type != "ftp" and type != "file":
                    continue
                mirror = subnode.text
                if mirror:
                    if mirror.endswith("/repodata/repomd.xml"):
                        mirror = mirror.replace("/repodata/repomd.xml", "")
                    elif filename and mirror.endswith("/"+filename):
                        mirror = mirror.replace("/"+filename, "")
                    if self._baseurl in self._mirrors:
                        if mirror not in self._mirrors[self._baseurl]:
                            self._mirrors[self._baseurl].append(mirror)
                    else:
                        self._mirrors[self._baseurl] = [mirror]

    def loadMirrors(self, mirrorlistfile):
        self._mirrors.clear()

        try:
            file = open(mirrorlistfile, 'r')
        except IOError, e:
            iface.warning(_("Could not load mirror list. Continuing with base URL only."))
            iface.debug(unicode(e))
            return

        for line in file:
            if line == '<?xml version="1.0" encoding="utf-8"?>\n':
                return self.loadMetalink(mirrorlistfile)
            if line[0] != "#":
                mirror = line.strip()
                if mirror:
                    if self._baseurl in self._mirrors:
                        if mirror not in self._mirrors[self._baseurl]:
                            self._mirrors[self._baseurl].append(mirror)
                    else:
                        self._mirrors[self._baseurl] = [mirror]

    def loadMetadata(self, metadatafile):
        info = {}

        try:
            root = ElementTree.parse(metadatafile).getroot()
        except (expat.error, SyntaxError), e: # ElementTree.ParseError
            raise Error, _("Invalid XML file:\n  %s\n  %s") % \
                          (metadatafile, str(e))

        for node in root.getchildren():
            if node.tag != DATA:
                continue
            type = node.get("type")
            info[type] = {}
            for subnode in node.getchildren():
                if subnode.tag == LOCATION:
                    info[type]["url"] = \
                        posixpath.join(self._baseurl, subnode.get("href"))
                if subnode.tag == CHECKSUM:
                    info[type][subnode.get("type")] = subnode.text
                if subnode.tag == OPENCHECKSUM:
                    info[type]["uncomp_"+subnode.get("type")] = \
                        subnode.text
        
        return info
        
    def getLocalPath(self, fetcher, url):
        from smart.fetcher import FetchItem
        mirror = fetcher.getMirrorSystem().get(url)
        item = FetchItem(fetcher, url, mirror)
        return fetcher.getLocalPath(item)

    def fetch(self, fetcher, progress):
        
        fetcher.reset()

        if self._mirrorlist:
            mirrorlist = self._mirrorlist
            item = fetcher.enqueue(mirrorlist)
            fetcher.run(progress=progress)

            if item.getStatus() is FAILED:
                progress.add(self.getFetchSteps()-1)
                if fetcher.getCaching() is NEVER:
                    iface.warning(_("Could not load mirror list. Continuing with base URL only."))
            else:
                self.loadMirrors(item.getTargetPath())

            fetcher.reset()
        else:
            progress.add(1)

        repomd = posixpath.join(self._baseurl, "repodata/repomd.xml")
        reposig = posixpath.join(self._baseurl, "repodata/repomd.xml.asc")

        oldinfo = {}
        path = self.getLocalPath(fetcher, repomd)
        if os.path.exists(path):
            try:
                oldinfo = self.loadMetadata(path)
            except Error:
                pass
        
        item = fetcher.enqueue(repomd)
        if self._fingerprint:
            gpgitem = fetcher.enqueue(reposig)
        fetcher.run(progress=progress)

        if item.getStatus() is FAILED:
            progress.add(self.getFetchSteps()-1)
            if fetcher.getCaching() is NEVER:
                lines = [_("Failed acquiring release file for '%s':") % self,
                         u"%s: %s" % (item.getURL(), item.getFailedReason())]
                raise Error, "\n".join(lines)
            return False

        if self._fingerprint:
            if gpgitem.getStatus() is FAILED:
                raise Error, \
                      _("Download of repomd.xml.asc failed for secure "
                        "channel '%s': %s") % (self, gpgitem.getFailedReason())

            status, output = commands.getstatusoutput(
                "gpg --batch --no-secmem-warning --status-fd 1 --verify "
                "%s %s" % (gpgitem.getTargetPath(), item.getTargetPath()))

            badsig = False
            goodsig = False
            validsig = None
            for line in output.splitlines():
                if line.startswith("[GNUPG:]"):
                    tokens = line[8:].split()
                    first = tokens[0]
                    if first == "VALIDSIG":
                        validsig = tokens[1]
                    elif first == "GOODSIG":
                        goodsig = True
                    elif first == "BADSIG":
                        badsig = True
            if badsig:
                raise Error, _("Channel '%s' has bad signature") % self
            if (not goodsig or
                (self._fingerprint and validsig != self._fingerprint)):
                raise Error, _("Channel '%s' signed with unknown key") % self

        digest = getFileDigest(item.getTargetPath())
        if digest == self._digest:
            progress.add(1)
            return True
        self.removeLoaders()

        info = self.loadMetadata(item.getTargetPath())

        if "primary" not in info and "primary_lzma" not in info:
            raise Error, _("Primary information not found in repository "
                           "metadata for '%s'") % self

        if "primary_lzma" in info:
            primary = info["primary_lzma"]
        else:
            primary = info["primary"]
        if "filelists_lzma" in info:
            filelists = info["filelists_lzma"]
        else:
            filelists = info["filelists"]

        fetcher.reset()
        item = fetcher.enqueue(primary["url"],
                               md5=primary.get("md5"),
                               uncomp_md5=primary.get("uncomp_md5"),
                               sha=primary.get("sha"),
                               uncomp_sha=primary.get("uncomp_sha"),
                               sha256=primary.get("sha256"),
                               uncomp_sha256=primary.get("uncomp_sha256"),
                               uncomp=True)
        flitem = fetcher.enqueue(filelists["url"],
                                 md5=filelists.get("md5"),
                                 uncomp_md5=filelists.get("uncomp_md5"),
                                 sha=filelists.get("sha"),
                                 uncomp_sha=filelists.get("uncomp_sha"),
                                 sha256=filelists.get("sha256"),
                                 uncomp_sha256=filelists.get("uncomp_sha256"),
                                 uncomp=True)
        if "updateinfo" in info:
            uiitem = fetcher.enqueue(info["updateinfo"]["url"],
                                   md5=info["updateinfo"].get("md5"),
                                   uncomp_md5=info["updateinfo"].get("uncomp_md5"),
                                   sha=info["updateinfo"].get("sha"),
                                   uncomp_sha=info["updateinfo"].get("uncomp_sha"),
                                   uncomp=True)
        fetcher.run(progress=progress)
 
        if item.getStatus() == SUCCEEDED and flitem.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            filelistspath = flitem.getTargetPath()
            loader = RPMMetaDataLoader(localpath, filelistspath,
                                       self._baseurl)
            loader.setChannel(self)
            self._loaders.append(loader)
            if "updateinfo" in info:
                if uiitem.getStatus() == SUCCEEDED:
                    localpath = uiitem.getTargetPath()
                    errata = RPMUpdateInfo(localpath)
                    errata.load()
                    errata.setErrataFlags()
                else:
                    iface.warning(_("Failed to download. You must fetch channel "
                        "information to acquire needed update information.\n"
                        "%s: %s") % (uiitem.getURL(), uiitem.getFailedReason()))
        elif (item.getStatus() == SUCCEEDED and
              flitem.getStatus() == FAILED and
              fetcher.getCaching() is ALWAYS):
            iface.warning(_("Failed to download. You must fetch channel "
                            "information to acquire needed filelists.\n"
                            "%s: %s") % (flitem.getURL(),
                            flitem.getFailedReason()))
            return False
        elif fetcher.getCaching() is NEVER:
            if item.getStatus() == FAILED:
                faileditem = item
            else:
                faileditem = flitem
            lines = [_("Failed acquiring information for '%s':") % self,
                       u"%s: %s" % (faileditem.getURL(),
                       faileditem.getFailedReason())]
            raise Error, "\n".join(lines)
        else:
            return False

        uncompressor = fetcher.getUncompressor()

        # delete any old files, if the new ones have new names
        for type in ["primary", "filelists", "other", 
                     "primary_lzma", "filelists_lzma", "other_lzma"]:
            if type in oldinfo:
                url = oldinfo[type]["url"]
                if url and info[type]["url"] != oldinfo[type]["url"]:
                    path = self.getLocalPath(fetcher, url)
                    if os.path.exists(path):
                       os.unlink(path)
                    handler = uncompressor.getHandler(path)
                    path = handler.getTargetPath(path)
                    if os.path.exists(path):
                       os.unlink(path)

        self._digest = digest

        return True

def create(alias, data):
    return RPMMetaDataChannel(data["baseurl"],
                              data["mirrorlist"],
                              data["fingerprint"],
                              data["type"],
                              alias,
                              data["name"],
                              data["manual"],
                              data["removable"],
                              data["priority"])

# vim:ts=4:sw=4:et

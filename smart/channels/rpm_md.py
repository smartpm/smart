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
from smart.util.filetools import getFileDigest
from smart.util.elementtree import ElementTree
from smart.const import SUCCEEDED, FAILED, NEVER
from smart.channel import PackageChannel
from smart import *
import posixpath

NS = "{http://linux.duke.edu/metadata/repo}"
DATA = NS+"data"
LOCATION = NS+"location"
CHECKSUM = NS+"checksum"
OPENCHECKSUM = NS+"open-checksum"

class RPMMetaDataChannel(PackageChannel):

    def __init__(self, baseurl, *args):
        super(RPMMetaDataChannel, self).__init__(*args)
        self._baseurl = baseurl

    def getCacheCompareURLs(self):
        return [posixpath.join(self._baseurl, "repodata/repomd.xml")]

    def getFetchSteps(self):
        return 2

    def fetch(self, fetcher, progress):
        
        fetcher.reset()
        repomd = posixpath.join(self._baseurl, "repodata/repomd.xml")
        item = fetcher.enqueue(repomd)
        fetcher.run(progress=progress)

        if item.getStatus() is FAILED:
            progress.add(1)
            if fetcher.getCaching() is NEVER:
                lines = ["Failed acquiring release file for '%s':" % self,
                         "%s: %s" % (item.getURL(), item.getFailedReason())]
                raise Error, "\n".join(lines)
            return False

        digest = getFileDigest(item.getTargetPath())
        if digest == self._digest:
            progress.add(1)
            return True
        self.removeLoaders()

        info = {}
        root = ElementTree.parse(item.getTargetPath()).getroot()
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

        if "primary" not in info:
            raise Error, "Primary information not found in repository " \
                         "metadata for '%s'" % self

        fetcher.reset()
        item = fetcher.enqueue(info["primary"]["url"],
                               md5=info["primary"].get("md5"),
                               uncomp_md5=info["primary"].get("uncomp_md5"),
                               uncomp=True)
        fetcher.run(progress=progress)

        if item.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            loader = RPMMetaDataLoader(localpath, self._baseurl)
            loader.setChannel(self)
            self._loaders.append(loader)
        else:
            lines = ["Failed acquiring information for '%s':" % self,
                     "%s: %s" % (item.getURL(), item.getFailedReason())]
            raise Error, "\n".join(lines)

        self._digest = digest

        return True

def create(alias, data):
    return RPMMetaDataChannel(data["baseurl"],
                              data["type"],
                              alias,
                              data["name"],
                              data["manual"],
                              data["removable"],
                              data["priority"])

# vim:ts=4:sw=4:et

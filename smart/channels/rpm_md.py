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
from smart.util.elementtree import ElementTree
from smart.util.strtools import strToBool
from smart.const import SUCCEEDED, FAILED, NEVER
from smart.channel import Channel
from smart import *
import posixpath

NS = "{http://linux.duke.edu/metadata/repo}"
DATA = NS+"data"
LOCATION = NS+"location"
CHECKSUM = NS+"checksum"
OPENCHECKSUM = NS+"open-checksum"

class RPMMetaDataChannel(Channel):

    def __init__(self, baseurl, *args):
        Channel.__init__(self, *args)
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
            self._loader = RPMMetaDataLoader(localpath, self._baseurl)
            self._loader.setChannel(self)
        else:
            lines = ["Failed acquiring information for '%s':" % self,
                     "%s: %s" % (item.getURL(), item.getFailedReason())]
            raise Error, "\n".join(lines)

        return True

def create(type, alias, data):
    name = None
    description = None
    priority = 0
    baseurl = None
    manual = False
    removable = False
    if isinstance(data, dict):
        name = data.get("name")
        description = data.get("description")
        priority = data.get("priority", 0)
        manual = strToBool(data.get("manual", False))
        removable = strToBool(data.get("removable", False))
        baseurl = data.get("baseurl")
    elif getattr(data, "tag", None) == "channel":
        for n in data.getchildren():
            if n.tag == "name":
                name = n.text
            elif n.tag == "description":
                description = n.text
            elif n.tag == "priority":
                priority = n.text
            elif n.tag == "manual":
                manual = strToBool(n.text)
            elif n.tag == "removable":
                removable = strToBool(n.text)
            elif n.tag == "baseurl":
                baseurl = n.text
    else:
        raise ChannelDataError
    if not baseurl:
        raise Error, "Channel '%s' has no baseurl" % alias
    try:
        priority = int(priority)
    except ValueError:
        raise Error, "Invalid priority"
    return RPMMetaDataChannel(baseurl, type, alias, name, description,
                              priority, manual, removable)

# vim:ts=4:sw=4:et

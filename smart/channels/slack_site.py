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
from smart.backends.slack.loader import SlackSiteLoader
from smart.channel import PackageChannel, ChannelDataError
from smart.util.strtools import strToBool
from smart.const import SUCCEEDED, FAILED, NEVER
from smart import *
import posixpath

class SlackSiteChannel(PackageChannel):

    def __init__(self, baseurl, *args):
        super(SlackSiteChannel, self).__init__(*args)
        self._baseurl = baseurl

    def getCacheCompareURLs(self):
        return [posixpath.join(self._baseurl, "PACKAGES.TXT")]

    def getFetchSteps(self):
        return 1

    def fetch(self, fetcher, progress):

        self._loader = None

        fetcher.reset()

        # Fetch packages file
        url = posixpath.join(self._baseurl, "PACKAGES.TXT")
        item = fetcher.enqueue(url)
        fetcher.run(progress=progress)
        if item.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            self._loader = SlackSiteLoader(localpath, self._baseurl)
            self._loader.setChannel(self)
        elif fetcher.getCaching() is NEVER:
            lines = ["Failed acquiring information for '%s':" % self,
                     "%s: %s" % (item.getURL(), item.getFailedReason())]
            raise Error, "\n".join(lines)

        return True

def create(type, alias, data):
    name = None
    priority = 0
    manual = False
    removable = False
    baseurl = None
    if isinstance(data, dict):
        name = data.get("name")
        priority = data.get("priority", 0)
        manual = strToBool(data.get("manual", False))
        removable = strToBool(data.get("removable", False))
        baseurl = data.get("baseurl")
    elif getattr(data, "tag", None) == "channel":
        for n in data.getchildren():
            if n.tag == "name":
                name = n.text
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
    return SlackSiteChannel(baseurl,
                            type, alias, name, manual, removable, priority)

# vim:ts=4:sw=4:et

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
from gepeto.backends.rpm.header import RPMHeaderListLoader
from gepeto.util.strtools import strToBool
from gepeto.const import SUCCEEDED, FAILED, NEVER
from gepeto.channel import Channel
from gepeto import *
import posixpath

class RPMHeaderListChannel(Channel):

    def __init__(self, hdlurl, baseurl, *args):
        Channel.__init__(self, *args)
        
        self._hdlurl = hdlurl
        self._baseurl = baseurl

    def getCacheCompareURLs(self):
        return [self._hdlurl]

    def getFetchSteps(self):
        return 1

    def fetch(self, fetcher, progress):
        fetcher.reset()
        item = fetcher.enqueue(self._hdlurl, uncomp=True)
        fetcher.run(progress=progress)
        if item.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            self._loader = RPMHeaderListLoader(localpath, self._baseurl)
            self._loader.setChannel(self)
        elif fetcher.getCaching() is NEVER:
            iface.warning("Failed acquiring information for '%s':" %
                          self._alias)
            iface.warning("%s: %s" % (item.getURL(), item.getFailedReason()))

def create(type, alias, data):
    name = None
    description = None
    priority = 0
    manual = False
    removable = False
    hdlurl = None
    baseurl = None
    if isinstance(data, dict):
        name = data.get("name")
        description = data.get("description")
        priority = data.get("priority", 0)
        manual = strToBool(data.get("manual", False))
        removable = strToBool(data.get("removable", False))
        hdlurl = data.get("hdlurl")
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
            elif n.tag == "hdlurl":
                hdlurl = n.text
            elif n.tag == "baseurl":
                baseurl = n.text
    else:
        raise ChannelDataError
    if not hdlurl:
        raise Error, "Channel '%s' has no hdlurl" % alias
    if not baseurl:
        raise Error, "Channel '%s' has no baseurl" % alias
    try:
        priority = int(priority)
    except ValueError:
        raise Error, "Invalid priority"
    return RPMHeaderListChannel(hdlurl, baseurl,
                                type, alias, name, description,
                                priority, manual, removable)

# vim:ts=4:sw=4:et

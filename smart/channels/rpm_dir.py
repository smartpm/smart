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
from smart.backends.rpm.header import RPMDirLoader
from smart.util.strtools import strToBool
from smart.channel import Channel
from smart import *
import os

class RPMDirChannel(Channel):

    def __init__(self, path, *args):
        Channel.__init__(self, *args)
        self._path = path

    def fetch(self, fetcher, progress):
        if not os.path.isdir(self._path):
            raise Error, "Channel '%s' has invalid directory: %s" % \
                         (self, self._path)
        self._loader = RPMDirLoader(self._path)
        self._loader.setChannel(self)

def create(type, alias, data):
    name = None
    description = None
    priority = 0
    manual = False
    removable = False
    path = None
    if isinstance(data, dict):
        name = data.get("name")
        description = data.get("description")
        priority = data.get("priority", 0)
        manual = strToBool(data.get("manual", False))
        removable = strToBool(data.get("removable", False))
        path = data.get("path")
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
            elif n.tag == "path":
                path = n.text
    else:
        raise ChannelDataError
    if not path:
        raise Error, "Channel '%s' has no path" % alias
    try:
        priority = int(priority)
    except ValueError:
        raise Error, "Invalid priority"
    if removable:
        raise Error, "%s channels cannot be removable" % type
    return RPMDirChannel(path, type, alias, name, description,
                         priority, manual, removable)

# vim:ts=4:sw=4:et

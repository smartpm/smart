#
# Copyright (c) 2008 afb datakonsult
#
# Written by Anders F Bjorklund <afb@users.sourceforge.net>
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
from smart.backends.deb.fink_virtual_pkgs import FinkVirtualPkgsLoader, FinkVirtualPkgInfo
from smart.channel import PackageChannel
from smart import *
import os
import sys
import string

class FinkVirtualPkgsChannel(PackageChannel):

    def __init__(self, path, *args):
        super(FinkVirtualPkgsChannel, self).__init__(*args)
        self._path = path

    def fetch(self, fetcher, progress):
        if not os.path.isfile(self._path):
            raise Error, _("Channel '%s' has invalid command: %s") % \
                         (self, self._path)
        self.removeLoaders()
        loader = FinkVirtualPkgsLoader(self._path)
        loader.setChannel(self)
        self._loaders.append(loader)
        return True

def create(alias, data):
    if data["removable"]:
        raise Error, _("%s channels cannot be removable") % data["type"]
    return FinkVirtualPkgsChannel(data["path"],
                         data["type"],
                         alias,
                         data["name"],
                         data["manual"],
                         data["removable"],
                         data["priority"])



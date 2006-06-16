#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Mauricio Teixeira <mteixeira@webset.net>
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
from smart.backends.rpm.yast2 import YaST2Loader
from smart.util.filetools import getFileDigest
from smart.const import SUCCEEDED, FAILED, NEVER
from smart.channel import PackageChannel
from smart import *
import posixpath
import tempfile
import commands
import os

class YaST2Channel(PackageChannel):
    def __init__(self, baseurl, *args):
        super(YaST2Channel, self).__init__(*args)
        self._baseurl = baseurl

    def getCacheCompareURLs(self):
	return [posixpath.join(self._baseurl, "media.1/media")]

    def getFetchSteps(self):
        return 4

    def __fetchFile(self, file, fetcher, progress):
        fetcher.reset()
        item = fetcher.enqueue(file)
        fetcher.run(progress=progress)
        failed = item.getFailedReason()
        if failed:
            progress.add(self.getFetchSteps()-1)
            progress.show()
            if fetcher.getCaching() is NEVER:
                lines = [_("Failed acquiring information for '%s':") % self,
                         "%s: %s" % (item.getURL(), failed)]
                raise Error, "\n".join(lines)
            return False
        return item

    def fetch(self, fetcher, progress):

        # Fetch media information file
        # This file contains the timestamp info
        # that says if the repository has changed
        fetchitem = posixpath.join(self._baseurl, "media.1/media")
        fetched = self.__fetchFile(fetchitem, fetcher, progress)
        if not fetched or fetched.getStatus() == FAILED: return False

        digest = getFileDigest(fetched.getTargetPath())
        #if digest == self._digest and getattr(self, "force-yast", False):
        if digest == self._digest:
            return True
        self.removeLoaders()

        # Find location of description files
        fetchitem = posixpath.join(self._baseurl, "content")
        fetched = self.__fetchFile(fetchitem, fetcher, progress)
        if not fetched or fetched.getStatus() == FAILED: return False
        self.removeLoaders()
        descrdir = "suse/setup/descr"
        datadir = "RPMS"
        for line in open(fetched.getTargetPath()):
            if line.startswith("DESCRDIR"): descrdir = line[9:-1]
            if line.startswith("DATADIR"): datadir = line[8:-1]

        # Fetch package information (req, dep, prov, etc)
        fetchitem = posixpath.join(self._baseurl,
                                  (("%s/packages") % descrdir))
        fetched = self.__fetchFile(fetchitem, fetcher, progress)
        if not fetched or fetched.getStatus() == FAILED: return False
        self.removeLoaders()
        pkginfofile = fetched.getTargetPath()
        if open(pkginfofile).read(9) == "=Ver: 2.0":
            fetchitem = posixpath.join(self._baseurl,
                                      (("%s/packages.en") % descrdir))
            fetched = self.__fetchFile(fetchitem, fetcher, progress)
            if not fetched or fetched.getStatus() == FAILED or open(fetched.getTargetPath()).read(9) != "=Ver: 2.0":
                raise Error, "YaST2 package descriptions not loaded."
                loader = YaST2Loader(self._baseurl, datadir, pkginfofile)
            else:
                pkgdescfile = fetched.getTargetPath()
                loader = YaST2Loader(self._baseurl, datadir, pkginfofile, pkgdescfile)
            loader.setChannel(self)
            self._loaders.append(loader)
        else:
            raise Error, _("Invalid package file format. Invalid header found.")

        self._digest = digest

        return True

def create(alias, data):
    return YaST2Channel(data["baseurl"],
                        data["type"],
                        alias,
                        data["name"],
                        data["manual"],
                        data["removable"],
                        data["priority"])

# vim:ts=4:sw=4:et

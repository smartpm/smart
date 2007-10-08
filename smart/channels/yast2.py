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
import posixpath

from smart.backends.rpm.yast2 import YaST2Loader
from smart.util.filetools import getFileDigest
from smart.const import FAILED, NEVER
from smart.channel import PackageChannel
from smart import Error, _


class YaST2Channel(PackageChannel):

    def __init__(self, baseurl, compressed, *args):
        super(YaST2Channel, self).__init__(*args)
        self._baseurl = baseurl
        self._compressed = compressed

    def getCacheCompareURLs(self):
        return [posixpath.join(self._baseurl, "media.1/media")]

    def getFetchSteps(self):
        return 4

    def __fetchFile(self, file, fetcher, progress, uncompress=False):
        fetcher.reset()
        item = fetcher.enqueue(file,uncomp=uncompress)
        fetcher.run(progress=progress)
        failed = item.getFailedReason()
        if failed:
            progress.add(self.getFetchSteps()-1)
            progress.show()
            if fetcher.getCaching() is NEVER:
                lines = [_("Failed acquiring information for '%s':") % self,
                         "%s: %s" % (item.getURL(), failed)]
                raise Error, "\n".join(lines)
        return item

    def fetch(self, fetcher, progress):

        # Fetch media information file
        # This file contains the timestamp info
        # that says if the repository has changed
        fetchitem = posixpath.join(self._baseurl, "media.1/media")
        fetched = self.__fetchFile(fetchitem, fetcher, progress)
        if fetched.getStatus() == FAILED:
            return False

        digest = getFileDigest(fetched.getTargetPath())
        #if digest == self._digest and getattr(self, "force-yast", False):
        if digest == self._digest:
            return True

        # Find location of description files
        fetchitem = posixpath.join(self._baseurl, "content")
        fetched = self.__fetchFile(fetchitem, fetcher, progress)
        if fetched.getStatus() == FAILED:
            return False

        descrdir = "suse/setup/descr"
        datadir = "RPMS"
        uncompress = self._compressed
        for line in open(fetched.getTargetPath()):
            line = line.strip()
            try:
                key, rest = line.split(None, 1)
            except ValueError:
                continue

            if key == "DESCRDIR":
                descrdir = rest
            elif key == "DATADIR":
                datadir = rest
            elif key == "META":
                # Autodetect compressed/uncompressed SuSEtags metadata.
                if rest.endswith("packages"):
                    uncompress = False
                elif rest.endswith("packages.gz"):
                    uncompress = True

        # Fetch package information (req, dep, prov, etc)
        fetchitem = posixpath.join(self._baseurl, "%s/packages" % descrdir)
        if uncompress:
            fetchitem += ".gz"
        fetched = self.__fetchFile(fetchitem, fetcher, progress, uncompress)
        if fetched.getStatus() == FAILED:
            return False

        self.removeLoaders()

        pkginfofile = fetched.getTargetPath()
        header = open(pkginfofile).readline().strip()
        if header == "=Ver: 2.0":
            fetchitem = posixpath.join(self._baseurl,
                                       "%s/packages.en" % descrdir)
            if uncompress:
                fetchitem += ".gz"

            fetched = self.__fetchFile(fetchitem, fetcher,
                                       progress, uncompress)

            if (fetched.getStatus() == FAILED or
                open(fetched.getTargetPath()).readline().strip() != "=Ver: 2.0"):
                raise Error, "YaST2 package descriptions not loaded."
            else:
                pkgdescfile = fetched.getTargetPath()
                loader = YaST2Loader(self._baseurl, datadir,
                                     pkginfofile, pkgdescfile)

            loader.setChannel(self)
            self._loaders.append(loader)
        else:
            raise Error, _("Invalid package file header (%s)" % header)

        self._digest = digest

        return True


def create(alias, data):
    return YaST2Channel(data["baseurl"],
                        data["compressed"],
                        data["type"],
                        alias,
                        data["name"],
                        data["manual"],
                        data["removable"],
                        data["priority"])

# vim:ts=4:sw=4:et

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
from smart.backends.rpm.header import URPMILoader
from smart.const import SUCCEEDED, FAILED, ALWAYS, NEVER
from smart.channel import PackageChannel
from smart import *
import posixpath
import os

class URPMIChannel(PackageChannel):

    def __init__(self, hdlurl, baseurl, *args):
        super(URPMIChannel, self).__init__(*args)
        self._hdlurl = hdlurl
        self._baseurl = baseurl

    def getCacheCompareURLs(self):
        return [posixpath.join(self._baseurl, "MD5SUM")]

    def getFetchSteps(self):
        return 2

    def fetch(self, fetcher, progress):

        fetcher.reset()

        url = posixpath.join(self._baseurl, "MD5SUM")
        item = fetcher.enqueue(url)
        fetcher.run(progress=progress)
        hdlmd5 = None
        failed = item.getFailedReason()
        if failed:
            progress.add(1)
            if fetcher.getCaching() is NEVER:
                lines = ["Failed acquiring information for '%s':" % self,
                         "%s: %s" % (item.getURL(), failed)]
                raise Error, "\n".join(lines)
            return False


        digest = getFileDigest(item.getTargetPath())
        if digest == self._digest:
            progress.add(1)
            return True
        self.removeLoaders()

        basename = posixpath.basename(self._hdlurl)
        for line in open(item.getTargetPath()):
            md5, name = line.split()
            if name == basename:
                hdlmd5 = md5
                break

        fetcher.reset()
        item = fetcher.enqueue(self._hdlurl, md5=hdlmd5, uncomp=True)
        fetcher.run(progress=progress)
        if item.getStatus() == FAILED:
            lines = ["Failed acquiring information for '%s':" % self,
                     "%s: %s" % (item.getURL(), failed)]
            raise Error, "\n".join(lines)
        else:
            localpath = item.getTargetPath()
            if localpath.endswith(".cz"):
                if (not os.path.isfile(localpath[:-3]) or
                    fetcher.getCaching() != ALWAYS):
                    linkpath = localpath[:-2]+"gz"
                    if os.path.isfile(linkpath):
                        os.unlink(linkpath)
                    os.symlink(localpath, linkpath)
                    uncompressor = fetcher.getUncompressor()
                    uncomphandler = uncompressor.getHandler(linkpath)
                    try:
                        uncomphandler.uncompress(linkpath)
                    except Error, e:
                        # cz file has trailing information which breaks
                        # current gzip module logic.
                        if "Not a gzipped file" not in e[0]:
                            os.unlink(linkpath)
                            raise
                    os.unlink(linkpath)
                localpath = localpath[:-3]
            loader = URPMILoader(localpath, self._baseurl)
            loader.setChannel(self)
            self._loaders.append(loader)

        self._digest = digest

        return True

def create(alias, data):
    return URPMIChannel(data["hdlurl"],
                        data["baseurl"],
                        data["type"],
                        alias,
                        data["name"],
                        data["manual"],
                        data["removable"],
                        data["priority"])

# vim:ts=4:sw=4:et

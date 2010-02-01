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
from smart.util.filetools import getFileDigest
from smart.channel import PackageChannel
from smart.const import SUCCEEDED, FAILED, NEVER
from smart import *
import posixpath
import commands

class SlackSiteChannel(PackageChannel):

    # It's important for the default to be here so that old pickled
    # instances which don't have these attributes still work fine.
    _fingerprint = None

    def __init__(self, baseurl, compressed, fingerprint, *args):
        super(SlackSiteChannel, self).__init__(*args)
        self._baseurl = baseurl
        self._compressed = compressed
        if fingerprint:
            self._fingerprint = "".join([x for x in fingerprint
                                         if not x.isspace()])
        else:
            self._fingerprint = None

    def getCacheCompareURLs(self):
        return [posixpath.join(self._baseurl, "PACKAGES.TXT")]

    def getFetchSteps(self):
        if self._fingerprint:
            return 3
        else:
            return 2

    def fetch(self, fetcher, progress):

        fetcher.reset()

        if self._compressed:
            PACKAGES_TXT="PACKAGES.TXT.gz"
            CHECKSUMS_md5="CHECKSUMS.md5.gz"
        else:
            PACKAGES_TXT="PACKAGES.TXT"
            CHECKSUMS_md5="CHECKSUMS.md5"

        # Fetch packages file
        url = posixpath.join(self._baseurl, PACKAGES_TXT)
        item = fetcher.enqueue(url, uncomp=self._compressed)
        fetcher.run(progress=progress)
        if item.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            digest = getFileDigest(localpath)
            if digest == self._digest:
                return True
            fetcher.reset()
            url = posixpath.join(self._baseurl, CHECKSUMS_md5)
            item = fetcher.enqueue(url, uncomp=self._compressed)
            if self._fingerprint:
                gpgurl = posixpath.join(self._baseurl, CHECKSUMS_md5 + ".asc")
                gpgitem = fetcher.enqueue(gpgurl)
            fetcher.run(progress=progress)
            if item.getStatus() == SUCCEEDED:
                checksumpath = item.getTargetPath()
            else:
                checksumpath = None
            if self._fingerprint:
                if gpgitem.getStatus() is SUCCEEDED:
                    try:
                        status, output = commands.getstatusoutput(
                            "gpg --batch --no-secmem-warning --status-fd 1 "
                            "--verify %s %s" % (gpgitem.getTargetPath(),
                                                item.getTargetPath()))
    
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
                        if not goodsig or validsig != self._fingerprint:
                            raise Error, _("Channel '%s' signed with unknown key") \
                                         % self
                    except Error, e:
                        progress.add(self.getFetchSteps()-2)
                        progress.show()
                        if fetcher.getCaching() is NEVER:
                            raise
                        else:
                            return False
            self.removeLoaders()
            loader = SlackSiteLoader(localpath, checksumpath, self._baseurl)
            loader.setChannel(self)
            self._loaders.append(loader)
        elif fetcher.getCaching() is NEVER:
            lines = [_("Failed acquiring information for '%s':") % self,
                     u"%s: %s" % (item.getURL(), item.getFailedReason())]
            raise Error, "\n".join(lines)
        else:
            return False

        self._digest = digest

        return True

def create(alias, data):
    return SlackSiteChannel(data["baseurl"],
                            data["compressed"],
                            data["fingerprint"],
                            data["type"],
                            alias,
                            data["name"],
                            data["manual"],
                            data["removable"],
                            data["priority"])

# vim:ts=4:sw=4:et

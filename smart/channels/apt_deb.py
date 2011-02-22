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
import posixpath
import commands

from smart.backends.deb.loader import DebTagFileLoader
from smart.util.filetools import getFileDigest
from smart.backends.deb.base import getArchitecture
from smart.channel import PackageChannel
from smart.const import SUCCEEDED, NEVER
from smart import *


class APTDEBChannel(PackageChannel):

    # It's important for the default to be here so that old pickled
    # instances which don't have these attributes still work fine.
    _fingerprint = None
    _keyring = None
    _trustdb = None
    _arch = None

    def __init__(self, baseurl, distro, comps, fingerprint, keyring, trustdb, *args):
        super(APTDEBChannel, self).__init__(*args)

        distro = distro.lstrip('/')
        self._baseurl = baseurl
        self._distro = distro
        self._comps = comps
        if fingerprint:
            self._fingerprint = "".join(fingerprint.split())
        if keyring:
            self._keyring = keyring
        if trustdb:
            self._trustdb = trustdb

    def _getURL(self, filename="", component=None, subpath=False):
        if self._arch is None:
            self._arch = getArchitecture()
        if subpath:
            distrourl = ""
        elif not self._comps:
            distrourl = posixpath.join(self._baseurl, self._distro)
        else:
            distrourl = posixpath.join(self._baseurl, "dists", self._distro)
        if component:
            return posixpath.join(distrourl, component,
                                 "binary-"+self._arch, filename)
        else:
            return posixpath.join(distrourl, filename)

    def getCacheCompareURLs(self):
        return [self._getURL("Release")]

    def getFetchSteps(self):
        if self._comps:
            # Packages*components + Release + Release.gpg
            return len(self._comps)+2
            # Component Release files are not being used, otherwise it'd be:
            # (Packages+Release)*components + Release + Release.gpg
            #return len(self._comps)*2+2
        else:
            # Packages + Release + Release.gpg
            return 3

    def _checkRelease(self, release_item, release_gpg_item):
        is_secure_channel = bool(self._fingerprint or self._keyring)
        need_release = bool(is_secure_channel or self._comps)
        release_failed = release_item.getFailedReason()

        if need_release and release_failed:
            raise Error, _("Download of Release failed for channel '%s': %s") \
                         % (self, release_failed)

        if is_secure_channel:
            release_gpg_failed = release_gpg_item.getFailedReason()
            if release_gpg_failed:
                raise Error, \
                      _("Download of Release.gpg failed for secure "
                        "channel '%s': %s") % (self, release_gpg_failed)

            arguments = ["gpg", "--batch", "--no-secmem-warning",
                         "--status-fd", "1"]

            if self._keyring:
                arguments.extend(["--no-default-keyring",
                                  "--keyring", self._keyring])

            if self._trustdb:
                arguments.extend(["--trustdb-name", self._trustdb])

            arguments.extend(["--verify",
                              release_gpg_item.getTargetPath(),
                              release_item.getTargetPath()])

            command = " ".join(arguments)
            status, output = commands.getstatusoutput(command)

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
            if (not goodsig or
                (self._fingerprint and validsig != self._fingerprint)):
                raise Error, _("Channel '%s' signed with unknown key") % self

    def _parseRelease(self, release_item):
        checksum = {}
        insidemd5sum = False
        insidesha1= False
        insidesha256= False
        for line in open(release_item.getTargetPath()):
            if not insidemd5sum:
                if line.startswith("MD5Sum:"):
                    insidemd5sum = True
            elif not line.startswith(" "):
                insidemd5sum = False
            elif insidemd5sum:
                try:
                    md5, size, path = line.split()
                except ValueError:
                    pass
                else:
                    if not path in checksum:
                        checksum[path] = {}
                    checksum[path]["md5"] = md5
                    checksum[path]["size"] = int(size)
            if not insidesha1:
                if line.startswith("SHA1:"):
                    insidesha1 = True
            elif not line.startswith(" "):
                insidesha1 = False
            elif insidesha1:
                try:
                    sha1, size, path = line.split()
                except ValueError:
                    pass
                else:
                    if not path in checksum:
                        checksum[path] = {}
                    checksum[path]["sha1"] = sha1
                    checksum[path]["size"] = int(size)
            if not insidesha256:
                if line.startswith("SHA256:"):
                    insidesha256 = True
            elif not line.startswith(" "):
                insidesha256 = False
            elif insidesha256:
                try:
                    sha256, size, path = line.split()
                except ValueError:
                    pass
                else:
                    if not path in checksum:
                        checksum[path] = {}
                    checksum[path]["sha256"] = sha256
                    checksum[path]["size"] = int(size)
        return checksum

    def _enqueuePackages(self, fetcher, checksum=None, component=None):
        info = {}
        url = self._getURL("Packages", component)
        subpath = self._getURL("Packages", component, subpath=True)
        if checksum is not None:
            if subpath+".lzma" in checksum:
                compressed_subpath = subpath+".lzma"
                url += ".lzma"
            elif subpath+".bz2" in checksum:
                compressed_subpath = subpath+".bz2"
                url += ".bz2"
            elif subpath+".gz" in checksum:
                compressed_subpath = subpath+".gz"
                url += ".gz"
            elif subpath in checksum:
                compressed_subpath = None
            else:
                return None
            if compressed_subpath:
                info["uncomp"] = True
                info["md5"] = checksum[compressed_subpath].get("md5", None)
                info["sha1"] = checksum[compressed_subpath].get("sha1", None)
                info["sha256"] = checksum[compressed_subpath].get("sha256", None)
                info["size"] = checksum[compressed_subpath]["size"]
                if subpath in checksum:
                    info["uncomp_md5"] = checksum[subpath].get("md5", None)
                    info["uncomp_sha1"] = checksum[subpath].get("sha1", None)
                    info["uncomp_sha256"] = checksum[subpath].get("sha256", None)
                    info["uncomp_size"] = checksum[subpath]["size"]
            else:
                info["md5"] = checksum[subpath].get("md5", None)
                info["sha1"] = checksum[subpath].get("sha1", None)
                info["sha256"] = checksum[subpath].get("sha256", None)
                info["size"] =  checksum[subpath]["size"]
        else:
            # Default to Packages.gz when we can't find out.
            info["uncomp"] = True
            url += ".gz"
        return fetcher.enqueue(url, **info)

    def fetch(self, fetcher, progress):

        fetcher.reset()

        # Fetch release file
        release_item = fetcher.enqueue(self._getURL("Release"))
        release_gpg_item = fetcher.enqueue(self._getURL("Release.gpg"))
        fetcher.run(progress=progress)

        try:
            self._checkRelease(release_item, release_gpg_item)
        except Error, e:
            progress.add(self.getFetchSteps()-2)
            progress.show()
            if fetcher.getCaching() is NEVER:
                raise
            else:
                return False

        if not release_item.getFailedReason():
            digest = getFileDigest(release_item.getTargetPath())
            if digest == self._digest:
                progress.add(self.getFetchSteps()-2)
                progress.show()
                return True
            self.removeLoaders()
            checksum = self._parseRelease(release_item)
        else:
            digest = None
            checksum = None

        fetcher.reset()

        if not self._comps:
            packages_items = [self._enqueuePackages(fetcher, checksum)]
        else:
            packages_items = []
            for component in self._comps:
                item = self._enqueuePackages(fetcher, checksum, component)
                if item:
                    packages_items.append(item)
                else:
                    iface.warning(_("Component '%s' is not in Release file "
                                    "for channel '%s'") % (component, self))

        fetcher.run(progress=progress)

        errorlines = []
        for item in packages_items:
            if item.getStatus() == SUCCEEDED:
                localpath = item.getTargetPath()
                loader = DebTagFileLoader(localpath, self._baseurl)
                loader.setChannel(self)
                self._loaders.append(loader)
            else:
                errorlines.append(u"%s: %s" % (item.getURL(),
                                               item.getFailedReason()))

        if errorlines:
            if fetcher.getCaching() is NEVER:
                errorlines.insert(0, _("Failed acquiring information for '%s':")
                                     % self)
                raise Error, "\n".join(errorlines)
            return False

        if digest:
            self._digest = digest

        return True


def create(alias, data):
    return APTDEBChannel(data["baseurl"],
                         data["distribution"],
                         data["components"].split(),
                         data["fingerprint"],
                         data["keyring"],
                         data["trustdb"],
                         data["type"],
                         alias,
                         data["name"],
                         data["manual"],
                         data["removable"],
                         data["priority"])

# vim:ts=4:sw=4:et

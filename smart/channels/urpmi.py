# -*- encoding: utf-8 -*-
# Copyright (c) 2005 Canonical
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
from smart.backends.rpm.synthesis import URPMISynthesisLoader
from smart.backends.rpm.header import URPMILoader
from smart.util.filetools import getFileDigest
from smart.const import SUCCEEDED, FAILED, ALWAYS, NEVER
from smart.channel import PackageChannel
from smart import *
import posixpath
import re
import os

class URPMIChannel(PackageChannel):

    def __init__(self, baseurl, hdlurl, *args):
        super(URPMIChannel, self).__init__(*args)
        self._baseurl = baseurl
        if hdlurl:
            if hdlurl[0] != "/" and ":/" not in hdlurl:
                self._hdlurl = posixpath.join(self._baseurl, hdlurl)
            else:
                self._hdlurl = hdlurl
        else:
            self._hdlurl = posixpath.join(self._baseurl, "hdlist.cz")
        self._compareurl = self._hdlurl

    def getCacheCompareURLs(self):
        return [self._compareurl]

    def getFetchSteps(self):
        return 4

    def fetch(self, fetcher, progress):

        fetcher.reset()

        self._compareurl = self._hdlurl

        hdlbaseurl, basename = os.path.split(self._hdlurl)

        md5url = posixpath.join(hdlbaseurl, "MD5SUM")
        item = fetcher.enqueue(md5url)
        fetcher.run(progress=progress)
        hdlmd5 = None
        failed = item.getFailedReason()
        if not failed:
            self._compareurl = md5url
            digest = getFileDigest(item.getTargetPath())
            if digest == self._digest:
                progress.add(3)
                return True

            basename = posixpath.basename(self._hdlurl)
            for line in open(item.getTargetPath()):
                line = line.strip()
                if line:
                    md5, name = line.split()
                    if name == basename:
                        hdlmd5 = md5
                        break

        fetcher.reset()
        hdlitem = fetcher.enqueue(self._hdlurl, md5=hdlmd5, uncomp=True)

        if self._hdlurl.endswith("/list"):
            listitem = None
        else:
            m = re.compile(r"/(?:synthesis\.)?hdlist(.*)\.") \
                  .search(self._hdlurl)
            suffix = m and m.group(1) or ""
            listurl = posixpath.join(hdlbaseurl, "list%s" % suffix)
            listitem = fetcher.enqueue(listurl, uncomp=True)

        descurl = posixpath.join(hdlbaseurl, "descriptions")
        descitem = fetcher.enqueue(descurl)

        fetcher.run(progress=progress)

        if hdlitem.getStatus() == FAILED:
            hdfailed = hdlitem.getFailedReason()
            if fetcher.getCaching() is NEVER:
                # Try reading reconfig.urpmi (should give new path)
                fetcher.reset()
                reconfigurl = posixpath.join(hdlbaseurl, "reconfig.urpmi")
                reconfigitem = fetcher.enqueue(reconfigurl)
                fetcher.run(progress=progress)
                if reconfigitem.getStatus() == FAILED:
                    refailed = reconfigitem.getFailedReason()
                    if fetcher.getCaching() is NEVER:
                        lines = [_("Failed acquiring information for '%s':") % self,
                            u"%s: %s" % (hdlitem.getURL(), hdfailed),
                            u"%s: %s" % (reconfigitem.getURL(), refailed)]
                        raise Error, "\n".join(lines)
                    return False
                else:
                    # Need to inject "/" at the end to avoid buggy urls
                    if not hdlbaseurl.endswith("/"): hdlbaseurl += "/"
                    for line in open(reconfigitem.getTargetPath()):
                        if line.startswith("#"): pass
                        elif line:
                            splitline = line.split()
                            arch = os.uname()[4]
                            if arch == "i686": arch = "i586"
                            reconfarch = re.sub("\$ARCH", arch, splitline[1])
                            reconfpath = re.sub(splitline[0] + "$", reconfarch, hdlbaseurl)
                            sysconf.set(("channels", self.getAlias(), \
                                        "baseurl"), reconfpath)
                            self._hdlurl = os.path.join(reconfpath, basename)
                    return self.fetch(fetcher, progress)
            return False
        else:
            localpath = hdlitem.getTargetPath()
            digestpath = None
            if listitem and listitem.getStatus() == SUCCEEDED:
                if self._compareurl == self._hdlurl:
                    self._compareurl = listurl
                    digestpath = localpath
                listpath = listitem.getTargetPath()
            else:
                listpath = None
                if self._compareurl == self._hdlurl:
                    digestpath = localpath
            if digestpath:
                digest = getFileDigest(digestpath)
                if digest == self._digest:
                    return True
            self.removeLoaders()
            if localpath.endswith(".cz"):
                if (not os.path.isfile(localpath[:-3]) or
                    fetcher.getCaching() != ALWAYS):
                    linkpath = fetcher.getLocalPath(hdlitem)
                    linkpath = linkpath[:-2]+"gz"
                    if not os.access(os.path.dirname(linkpath), os.W_OK):
                        dirname = os.path.join(sysconf.get("user-data-dir"),
                                               "channels")
                        basename = os.path.basename(linkpath)
                        if not os.path.isdir(dirname):
                            os.makedirs(dirname)
                        linkpath = os.path.join(dirname, basename)
                    if os.path.isfile(linkpath):
                        os.unlink(linkpath)
                    os.symlink(localpath, linkpath)
                    localpath = linkpath
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

            flagdict = {}
            if descitem and descitem.getStatus() == SUCCEEDED:
                descpath = descitem.getTargetPath()
                flagdict = self.getDescriptionFlags(descpath)
            
            if open(localpath).read(4) == "\x8e\xad\xe8\x01":
                loader = URPMILoader(localpath, self._baseurl, listpath, flagdict)
            else:
                loader = URPMISynthesisLoader(localpath, self._baseurl, listpath, flagdict)
                                
            loader.setChannel(self)
            self._loaders.append(loader)

        self._digest = digest

        return True

    def getDescriptionFlags(self, descpath):

        flagdict = {}
        try:
            packages = []
            update = importance = None
            pre = description = ""
            for line in open(descpath):
                if line.startswith("%package "):
                    if packages:
                        # TODO save pre/description for packages
                        pass
                    packages = line[(9):].rstrip("\n").split(" ")
                    in_pre = in_description = False
                    update = importance = None
                    pre = description = ""
                if line.startswith("Update: "):
                    update = line[8:].rstrip("\n")
                if line.startswith("Importance: "):
                    importance = line[12:].rstrip("\n")
                    for pkg in packages:
                        #iface.debug("%s: %s" % (pkg, importance))
                        flagdict[pkg] = importance
                if in_description:
                    description = description + line
                if line.startswith("%description"):
                    in_description = True
                    in_pre = False
                if in_pre:
                    pre = pre + line
                if line.startswith("%pre"):
                    in_pre = True
                    in_description = False
        except (IOError):
            pass

        return flagdict

def create(alias, data):
    return URPMIChannel(data["baseurl"],
                        data["hdlurl"],
                        data["type"],
                        alias,
                        data["name"],
                        data["manual"],
                        data["removable"],
                        data["priority"])

# vim:ts=4:sw=4:et

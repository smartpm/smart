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
from gepeto.backends.rpm.header import URPMILoader
from gepeto.const import SUCCEEDED, FAILED, ALWAYS, NEVER
from gepeto.util.strtools import strToBool
from gepeto.channel import Channel
from gepeto import *
import posixpath
import os

class URPMIChannel(Channel):

    def __init__(self, hdlurl, baseurl, *args):
        Channel.__init__(self, *args)
        
        self._hdlurl = hdlurl
        self._baseurl = baseurl

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
            if fetcher.getCaching() is NEVER:
                iface.warning("Failed acquiring information for '%s':" %
                              self._alias)
                iface.warning("%s: %s" % (item.getURL(), failed))
        else:
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
            iface.warning("Failed acquiring information for '%s':" %
                          self._alias)
            iface.warning("%s: %s" % (item.getURL(), item.getFailedReason()))
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
            self._loader = URPMILoader(localpath, self._baseurl)
            self._loader.setChannel(self)

def create(type, alias, data):
    name = None
    description = None
    priority = 0
    manual = False
    hdlurl = None
    baseurl = None
    if isinstance(data, dict):
        name = data.get("name")
        description = data.get("description")
        priority = data.get("priority", 0)
        manual = strToBool(data.get("manual", False))
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
    return URPMIChannel(hdlurl, baseurl,
                        type, alias, name, description, priority, manual)

# vim:ts=4:sw=4:et

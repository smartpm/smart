#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# Archlinux module written by Cody Lee (aka. platinummonkey) <platinummonkey@archlinux.us>
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
from smart.backends.arch.loader import ArchSiteLoader
from smart.util.filetools import getFileDigest
from smart.channel import PackageChannel
from smart.const import SUCCEEDED, FAILED, NEVER
from smart import *
import posixpath,  urllib2,  re

siteDBRE = re.compile("^(.+) (.+\.db\.tar\.gz)?$")

class ArchSiteChannel(PackageChannel):

    def __init__(self, baseurl, treename, *args):
        super(ArchSiteChannel, self).__init__(*args)
        self._baseurl = baseurl
        if not treename:
            treename = "" # TODO, get part before /os/
        self._treename = treename
        self._dbfile = treename + ".db.tar.gz"

    def getCacheCompareURLs(self):
        dbfile = getDBFile2()
        return [posixpath.join(self._baseurl, dbfile)]

    def getDBFile(self):
        # Find the correct *.db.tar.gz file since its different for each repository
        try: 
            dbfile = urllib2.urlopen(posixpath.join(self._baseurl, self._dbfile)) #This is able to handle all, http, https, and ftp protocols
        except HTTPError,  e:
            raise "HTTPERROR in smart/smart/channels/arch_site.py ==> %s" % e.reason
        except URLError,  e:
            raise "URLERROR in smart/smart/channels/arch_site.py ==> %s" % e.reason
        else:
            #html = response.readline(); m = ''; i=0
            #while not m:
            #    m = siteDBRE.match(html.rstrip())
            #    html = response.readline()
            #    i+=1;
            #    if i > 2000:
            #        raise "ERROR: *.db.tar.gz not found!"
            #        break # infinite loops are nasty...
            #dbfile = m.groups()[-1]
            #iface.warning(_("Got DB file via getDBFile"))
            return dbfile
    
    def getDBFile2(self,  url):
        spliturl = url.split('/')
        dbtags = ["core", "current", "community", "extra", "testing", "unstable"]
        for tag in dbtags:
            if tag in spliturl:
                dbfile = tag
        if not dbfile:
            iface.warning(_("Coudlnt find db.tar.gz in repo! Check to make sure the BaseURL is correct! BaseURL: %s") % self._baseurl)
            dbfile = None
        #self._filename = dbfile + ".db.tar.gz"
        return dbfile + ".db.tar.gz"

    def getFetchSteps(self):
        return 4 #1

    def fetch(self, fetcher, progress):
        #iface.warning(_("Getting via getDBFile"))
        self.getDBFile()
        #iface.warning(_("Getting via builtin Fetch"))
        fetcher.reset()
        #iface.warning(_("fetch: dbilfe = %s") % self._dbfile)
        # Fetch packages file
        url = posixpath.join(self._baseurl, self._dbfile)
        item = fetcher.enqueue(url,  uncomp=False)
        fetcher.run(progress=progress)
        if item.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            digest = getFileDigest(localpath)
            if digest == self._digest:
                return True
            self.removeLoaders()
            loader = ArchSiteLoader(localpath, self._baseurl)
            loader.setChannel(self)
            self._loaders.append(loader)
        elif fetcher.getCaching() is NEVER:
            lines = [_("Failed acquiring information for '%s':") % self,
                     u"%s: %s" % (item.getURL(), item.getFailedReason())]
            raise Error, "\n".join(lines)
        else:
            #iface.warning(_("FAILED FETCH: else statement in fetch"))
            return False

        self._digest = digest

        return True

def create(alias, data):
    return ArchSiteChannel(data["baseurl"],
                           data["treename"],
                           data["type"],
                           alias,
                           data["name"],
                           data["manual"],
                           data["removable"],
                           data["priority"])

# vim:ts=4:sw=4:et

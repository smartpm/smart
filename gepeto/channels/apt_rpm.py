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
from gepeto.backends.rpm.header import RPMPackageListLoader
from gepeto.channel import Channel, ChannelDataError
from gepeto.util.strtools import strToBool
from gepeto.const import SUCCEEDED, FAILED, NEVER
from gepeto.cache import LoaderSet
from gepeto import *
import posixpath
import tempfile
import commands
import os

class APTRPMChannel(Channel):

    def __init__(self, baseurl, comps, fingerprint, *args):
        Channel.__init__(self, *args)
        
        self._baseurl = baseurl
        self._comps = comps
        if fingerprint:
            self._fingerprint = "".join([x for x in fingerprint
                                         if not x.isspace()])
        else:
            self._fingerprint = None

        self._loader = LoaderSet()

    def getFetchSteps(self):
        return len(self._comps)*2+1

    def fetch(self, fetcher, progress):

        fetcher.reset()

        # Fetch release file
        url = posixpath.join(self._baseurl, "base/release")
        item = fetcher.enqueue(url)
        fetcher.run(progress=progress)
        failed = item.getFailedReason()
        if failed:
            if fetcher.getCaching() is NEVER:
                iface.warning("Failed acquiring release file for '%s':" %
                              self._alias)
                iface.warning("%s: %s" % (url, failed))
            progress.add(len(self._comps)*2)
            progress.show()
            return

        # Parse release file
        md5sum = {}
        insidemd5sum = False
        hassignature = False
        for line in open(item.getTargetPath()):
            if line.startswith("-----BEGIN"):
                hassignature = True
                break
            elif not insidemd5sum:
                if line.startswith("MD5Sum:"):
                    insidemd5sum = True
            elif not line.startswith(" "):
                insidemd5sum = False
            else:
                try:
                    md5, size, path = line.split()
                except ValueError:
                    pass
                else:
                    md5sum[path] = (md5, int(size))

        if self._fingerprint:
            rfd, rname = tempfile.mkstemp()
            sfd, sname = tempfile.mkstemp()
            rfile = os.fdopen(rfd, "w")
            sfile = os.fdopen(sfd, "w")
            try:
                if not hassignature:
                    raise Error, "Channel '%s' has fingerprint but is not " \
                                 "signed" % (self.getName() or self.getAlias())

                file = rfile
                for line in open(item.getTargetPath()):
                    if line.startswith("-----BEGIN"):
                        file = sfile
                    file.write(line)
                rfile.close()
                sfile.close()

                status, output = commands.getstatusoutput(
                    "gpg --batch --no-secmem-warning --status-fd 1 "
                    "--verify %s %s" % (sname, rname))

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
                    raise Error, "Channel '%s' has bad signature" \
                                 % (self.getName() or self.getAlias())
                if not goodsig or validsig != self._fingerprint:
                    raise Error, "Channel '%s' signed with unknown key" \
                                 % (self.getName() or self.getAlias())
            except Error, e:
                iface.error(str(e))
                progress.add(len(self._comps)*2)
                progress.show()
                rfile.close()
                sfile.close()
                os.unlink(rname)
                os.unlink(sname)
                return
            else:
                os.unlink(rname)
                os.unlink(sname)

        # Fetch component package lists and release files
        fetcher.reset()
        pkgitems = []
        relitems = []
        for comp in self._comps:
            pkglist = "base/pkglist."+comp
            url = posixpath.join(self._baseurl, pkglist)
            if pkglist+".bz2" in md5sum:
                upkglist = pkglist
                pkglist += ".bz2"
                url += ".bz2"
            elif pkglist+".gz" in md5sum:
                upkglist = pkglist
                pkglist += ".gz"
                url += ".gz"
            elif pkglist not in md5sum:
                iface.warning("Component '%s' is not in release file" % comp)
                continue
            else:
                upkglist = None
            info = {"component": comp, "uncomp": True}
            info["md5"], info["size"] = md5sum[pkglist]
            if upkglist:
                info["uncomp_md5"], info["uncomp_size"] = md5sum[upkglist]
            pkgitems.append(fetcher.enqueue(url, **info))

            release = "base/release."+comp
            if release in md5sum:
                url = posixpath.join(self._baseurl, release)
                info = {"component": comp}
                info["md5"], info["size"] = md5sum[release]
                relitems.append(fetcher.enqueue(url, **info))
            else:
                progress.add(1)
                progress.show()
                relitems.append(None)

        fetcher.run(progress=progress)

        firstfailure = True
        for i in range(len(pkgitems)):
            pkgitem = pkgitems[i]
            relitem = relitems[i]
            if pkgitem.getStatus() == SUCCEEDED:
                count = None
                if relitem and relitem.getStatus() == SUCCEEDED:
                    try:
                        for line in open(relitem.getTargetPath()):
                            if line.startswith("PackageCount:"):
                                count = int(line[13:])
                                break
                    except (IOError, ValueError):
                        pass
                localpath = pkgitem.getTargetPath()
                loader = RPMPackageListLoader(localpath, self._baseurl, count)
                loader.setChannel(self)
                self._loader.append(loader)
            else:
                if firstfailure:
                    firstfailure = False
                    iface.warning("Failed acquiring information for '%s':" %
                                  self._alias)
                iface.warning("%s: %s" %
                              (pkgitem.getURL(), pkgitem.getFailedReason()))

def create(type, alias, data):
    name = None
    description = None
    priority = 0
    manual = False
    baseurl = None
    comps = None
    fingerprint = None
    if isinstance(data, dict):
        name = data.get("name")
        description = data.get("description")
        baseurl = data.get("baseurl")
        comps = (data.get("components") or "").split()
        priority = data.get("priority", 0)
        manual = strToBool(data.get("manual", False))
        fingerprint = data.get("fingerprint")
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
            elif n.tag == "baseurl":
                baseurl = n.text
            elif n.tag == "components":
                comps = n.text.split()
    else:
        raise ChannelDataError
    if not baseurl:
        raise Error, "Channel '%s' has no baseurl" % alias
    if not comps:
        raise Error, "Channel '%s' has no components" % alias
    try:
        priority = int(priority)
    except ValueError:
        raise Error, "Invalid priority"
    return APTRPMChannel(baseurl, comps, fingerprint,
                         type, alias, name, description, priority, manual)

# vim:ts=4:sw=4:et

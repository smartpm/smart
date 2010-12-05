#
# Copyright (c) 2005 Canonical
# Copyright (c) 2004 Conectiva, Inc.
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
from smart.backends.rpm.base import *

try:
    from xml.etree import cElementTree        
except ImportError:
    try:
        import cElementTree
    except ImportError:     
        from smart.util import cElementTree

from smart import *
import re
import os

NS_UPDATEINFO = "http://novell.com/package/metadata/suse/updateinfo"

#def nstag(ns, tag):
#    return "{%s}%s" % (ns, tag)
def nstag(ns, tag):
    return tag

class RPMUpdateInfo:

    def __init__(self, filename):
        self._filename = filename
        self._flagdict = {}
        self._details = {}

    def load(self):
        UPDATES     = nstag(NS_UPDATEINFO, "updates")
        UPDATE      = nstag(NS_UPDATEINFO, "update")
        ID          = nstag(NS_UPDATEINFO, "id")
        TITLE       = nstag(NS_UPDATEINFO, "title")
        RELEASE     = nstag(NS_UPDATEINFO, "release")
        ISSUED      = nstag(NS_UPDATEINFO, "issued")
        REBOOT      = nstag(NS_UPDATEINFO, "reboot_suggested")
        REFERENCES  = nstag(NS_UPDATEINFO, "references")
        REFERENCE   = nstag(NS_UPDATEINFO, "reference")
        DESCRIPTION = nstag(NS_UPDATEINFO, "description")
        PKGLIST     = nstag(NS_UPDATEINFO, "pkglist")
        COLLECTION  = nstag(NS_UPDATEINFO, "collection")
        NAME        = nstag(NS_UPDATEINFO, "name")
        PACKAGE     = nstag(NS_UPDATEINFO, "package")
        FILENAME    = nstag(NS_UPDATEINFO, "filename")

        # Prepare package information.
        id = None
        type = None
        info = {}

        # Prepare data useful for the iteration
        skip = None
        packagelist = False
        references = True
        queue = []

        file = open(self._filename)
        for event, elem in cElementTree.iterparse(file, ("start", "end")):
            tag = elem.tag
            if tag.startswith("{"): (ns,tag)=tag.split("}") # skip namespace

            if event == "start":

                if tag == UPDATE:

                    # security
                    # bugfix
                    # enhancement
                    # recommended
                    type = elem.get("type")
                    if type == 'newpackage':
                        skip = UPDATE
                    info["type"] = type

                elif tag == REFERENCES:
                    references = True

                elif tag == PKGLIST:
                    packagelist = True

                queue.append(elem)

            elif event == "end":

                assert queue.pop() is elem

                if skip:
                    if tag == skip:
                        skip = None

                elif tag == ID:
                    id = elem.text
                    info["id"] = id

                elif tag == TITLE:
                    info["title"] = elem.text

                elif tag == ISSUED:
                    info["issued_date"] = elem.get("date")

                elif tag == REBOOT:
                    info["reboot_suggested"] = bool(elem.text)

                elif tag == DESCRIPTION:
                    if elem.text:
                        info["description"] = elem.text

                elif tag == REFERENCES:
                    references = False

                elif tag == REFERENCE:

                    href = elem.get("href")

                    if "references" in info:
                        info["references"].append(href)
                    else:
                        info["references"] = [href]

                elif tag == PKGLIST:
                    packagelist = False

                elif tag == PACKAGE:

                    name = elem.get("name")
                    e = elem.get("epoch")
                    v = elem.get("version")
                    r = elem.get("release")
                    arch = elem.get("arch")
                    
                    if arch == "src":
                        continue
                    elif name.endswith("-debuginfo"):
                        continue
                    elif rpm.archscore(arch) == 0:
                        continue

                    version = v
                    if e and e != "None" and e != "0":
                        version = "%s:%s" % (e, version)
                    if r:
                        version = "%s-%s" % (version, r)
                    versionarch = "%s@%s" % (version, arch)

                    #iface.debug("%s-%s: %s" % (name, versionarch, type))
                    if type:
                        pkg = "%s=%s" % (name, versionarch)
                        self._flagdict[pkg] = type
                    if info:
                        pkg = "%s=%s" % (name, versionarch)
                        self._details[pkg] = info

                elif tag == UPDATE:

                    # Reset all information.
                    id = None
                    type = None

                    # Do not clear it.
                    info = {}

                elem.clear()

        file.close()
        
    def getErrataFlags(self):
        return self._flagdict

    def setErrataFlags(self):
        # Can't set flags when in read-only mode
        if sysconf.getReadOnly():
            return

        for pkg, type in self._flagdict.iteritems():
            (name, version) = pkg.split("=")
            pkgconf.setFlag(type, name, "=", version)

    def getType(self, package):
        pkg = "%s=%s" % (package.name, package.version)
        return self._flagdict.get(pkg, None)

    def getInfo(self, package):
        pkg = "%s=%s" % (package.name, package.version)
        return self._details.get(pkg, None)


# vim:ts=4:sw=4:et

#
# Copyright (c) 2009 Smart Package Manager Team.
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
from smart.mirror import MirrorSystem
from smart.cache import Package, PackageInfo

import os
import urllib

try:
    from xml.etree import ElementTree
except ImportError:
    try:
        from elementtree import ElementTree
    except ImportError:
        from smart.util.elementtree import ElementTree

class Metalink:
    def __init__(self, mirrorsystem=None):
        self._metalink = ElementTree.Element("metalink")
        self._metalink.attrib["version"] = "3.0"
        self._metalink.attrib["xmlns"] = "http://www.metalinker.org/"
        self._metalink.attrib["generator"] = "smart"
        self._files = ElementTree.SubElement(self._metalink, "files")
        self._mirrorsystem = mirrorsystem or MirrorSystem()
    
    def append(self, info):
        for url in info.getURLs():
            file = ElementTree.SubElement(self._files, "file")
            description = ElementTree.SubElement(file, "description")
            description.text = info.getSummary().encode('utf-8')
            if info.getPackage():
                identity = ElementTree.SubElement(file, "identity")
                identity.text = info.getPackage().name
                version = ElementTree.SubElement(file, "version")
                version.text = info.getPackage().version
            resources = ElementTree.SubElement(file, "resources")
            if info.getSize(url):
                size = ElementTree.SubElement(file, "size")
                size.text = str(info.getSize(url))
            verification = ElementTree.SubElement(file, "verification")
            if info.getMD5(url):
                hashelem = ElementTree.Element("hash")
                hashelem.attrib["type"] = "md5"
                hashelem.text = info.getMD5()
                verification.append(hashelem)
            if info.getSHA(url):
                hashelem = ElementTree.Element("hash")
                hashelem.attrib["type"] = "sha1"
                hashelem.text = info.getSHA(url)
                verification.append(hashelem)
            if info.getSHA256(url):
                hashelem = ElementTree.Element("hash")
                hashelem.attrib["type"] = "sha256"
                hashelem.text = info.getSHA256(url)
                verification.append(hashelem)
            mirror = self._mirrorsystem.get(url)
            mirrorurl = mirror.getNext()
            while mirrorurl:
                if mirrorurl.startswith("/"):
                    scheme = "file"
                else:
                    scheme = urllib.splittype(mirrorurl)[0]
                country = None # country code ("US")
                priority = None # priority (100-1)
                filename = os.path.basename(mirrorurl)
                
                urlelem = ElementTree.Element("url")
                file.attrib["name"] = filename
                urlelem.attrib["type"] = scheme
                if country:
                    urlelem.attrib["location"] = country
                if priority:
                    urlelem.attrib["preference"] = str(priority)
                urlelem.text = mirrorurl
                resources.append(urlelem)
                mirrorurl = mirror.getNext()
    
    def write(self, output):
        if not output.isatty():
           output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        ElementTree.ElementTree(self._metalink).write(output)

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
import os
import urllib

try:
    from xml.etree import ElementTree
except ImportError:
    try:
        from elementtree import ElementTree
    except ImportError:
        from smart.util.elementtree import ElementTree

NS_METALINKER = "http://www.metalinker.org/"

def nstag(ns, tag):
    return "{%s}%s" % (ns, tag)

class Metafile:
    def __init__(self, name=None, version=None, summary=None):
        self._file = ElementTree.Element("file")
        if name:
            identityelem = ElementTree.SubElement(self._file, "identity")
            identityelem.text = name
        if version:
            versionelem = ElementTree.SubElement(self._file, "version")
            versionelem.text = version
        if summary:
            descelem = ElementTree.SubElement(self._file, "description")
            descelem.text = summary.encode('utf-8')
        self._resources = ElementTree.SubElement(self._file, "resources")
        self._info = {}
        self._urls = []

    def append(self, urls, **info):
        self._info = info
        if "size" in info and info["size"]:
            sizeelem = ElementTree.SubElement(self._file, "size")
            sizeelem.text = str(info["size"])
        verification = ElementTree.SubElement(self._file, "verification")
        if "md5" in info and info["md5"]:
            hashelem = ElementTree.Element("hash")
            hashelem.attrib["type"] = "md5"
            hashelem.text = info["md5"]
            verification.append(hashelem)
        if "sha" in info and info["sha"]:
            hashelem = ElementTree.Element("hash")
            hashelem.attrib["type"] = "sha1"
            hashelem.text = info["sha"]
            verification.append(hashelem)
        if "sha256" in info and info["sha256"]:
            hashelem = ElementTree.Element("hash")
            hashelem.attrib["type"] = "sha256"
            hashelem.text = info["sha256"]
            verification.append(hashelem)

        self._urls = urls
        for url in urls:
            if url.startswith("/"):
                scheme = "file"
            else:
                scheme = urllib.splittype(url)[0]
            country = None # country code ("US")
            priority = None # priority (100-1)
            filename = os.path.basename(url)

            urlelem = ElementTree.Element("url")
            urlelem.attrib["type"] = scheme
            if country:
                urlelem.attrib["location"] = country
            if priority:
                urlelem.attrib["preference"] = str(priority)
            urlelem.text = url
            self._resources.append(urlelem)
            self._file.attrib["name"] = filename
      
    def element(self):
        return self._file

    def info(self):
        return self._info

    def urls(self):
        return self._urls

class Metalink:
    def __init__(self, generator="smart"):
        self._metalink = ElementTree.Element("metalink")
        self._metalink.attrib["version"] = "3.0"
        self._metalink.attrib["xmlns"] = NS_METALINKER
        self._metalink.attrib["generator"] = generator
        self._files = ElementTree.SubElement(self._metalink, "files")
        self._metafiles = []
    
    def parse(self, input):
        metalink = Metalink()
        for event, elem in ElementTree.iterparse(input, ("start", "end")):
            tag = elem.tag
            if event == "start":
               if tag == nstag(NS_METALINKER, "file"):
                  name = None
                  version = None
                  summary = None
                  info = {}
                  urls = []
            elif event == "end":
               if tag == nstag(NS_METALINKER, "file"):
                  metafile = Metafile(name, version, summary)
                  metafile.append(urls, **info)
                  metalink.append(metafile)
               elif tag == nstag(NS_METALINKER, "identity"):
                  name = elem.text
               elif tag == nstag(NS_METALINKER, "version"):
                  version = elem.text
               elif tag == nstag(NS_METALINKER, "description"):
                  summary = unicode(elem.text)
               elif tag == nstag(NS_METALINKER, "url"):
                  urls.append(elem.text)
               elif tag == nstag(NS_METALINKER, "size"):
                  info["size"] = long(elem.text)
               elif tag == nstag(NS_METALINKER, "hash"):
                  type = elem.get("type")
                  if type == "sha1":
                      type = "sha"
                  info[type] = elem.text
                  
        return metalink
    parse = classmethod(parse)

    def append(self, file):
        self._files.append(file.element())
        self._metafiles.append(file)
    
    def files(self):
        return self._metafiles
    
    def write(self, output):
        if not output.isatty():
           output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        ElementTree.ElementTree(self._metalink).write(output)

if __name__ == "__main__":
    import sys
    Metalink.parse(open(sys.argv[1])).write(sys.stdout)


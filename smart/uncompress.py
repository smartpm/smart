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
import os

from smart.const import BLOCKSIZE
from smart import *

class Uncompressor(object):

    _handlers = [] 

    def addHandler(self, handler):
        self._handlers.append(handler())
    addHandler = classmethod(addHandler)

    def getHandler(self, localpath):
        for handler in self._handlers:
            if handler.query(localpath):
                return handler
    getHandler = classmethod(getHandler)

    def uncompress(self, localpath):
        for handler in self._handlers:
            if handler.query(localpath):
                return handler.uncompress(localpath)
        else:
            raise Error, _("Unknown compressed file: %s") % localpath

class UncompressorHandler(object):

    def query(self, localpath):
        return None

    def getTargetPath(self, localpath):
        return None

    def uncompress(self, localpath):
        raise Error, _("Unsupported file type")

class BZ2Handler(UncompressorHandler):

    def query(self, localpath):
        if localpath.endswith(".bz2"):
            return True

    def getTargetPath(self, localpath):
        return localpath[:-4]

    def uncompress(self, localpath):
        import bz2
        try:
            input = bz2.BZ2File(localpath)
            output = open(self.getTargetPath(localpath), "w")
            data = input.read(BLOCKSIZE)
            while data:
                output.write(data)
                data = input.read(BLOCKSIZE)
        except (IOError, OSError), e:
            raise Error, "%s: %s" % (localpath, e)
        except EOFError, e:
            raise Error, ("%s\nPossibly corrupted channel file.") % e

Uncompressor.addHandler(BZ2Handler)

class LZMAHandler(UncompressorHandler):

    def query(self, localpath):
        if localpath.endswith(".lzma"):
            return True

    def getTargetPath(self, localpath):
        if localpath.endswith(".lzma"):
            return localpath[:-5]

    def uncompress(self, localpath):
        try:
            import lzma
        except ImportError, e:
            unlzma = sysconf.get("unlzma", "unlzma")
            localpath = os.path.abspath(localpath)
            if os.system("%s <%s >%s 2>/dev/null" % (unlzma, localpath,
                         self.getTargetPath(localpath))) == 0:
                return
            raise Error, "%s, unlzma helper could not be found" % e
        try:
            input = lzma.LZMAFile(localpath)
            output = open(self.getTargetPath(localpath), "w")
            data = input.read(BLOCKSIZE)
            while data:
                output.write(data)
                data = input.read(BLOCKSIZE)
        except (IOError, OSError), e:
            raise Error, "%s: %s" % (localpath, e)
        except EOFError, e:
            raise Error, ("%s\nPossibly corrupted channel file.") % e

Uncompressor.addHandler(LZMAHandler)


class XZHandler(UncompressorHandler):

    def query(self, localpath):
        if localpath.endswith(".xz"):
            return True

    def getTargetPath(self, localpath):
        if localpath.endswith(".xz"):
            return localpath[:-3]

    def uncompress(self, localpath):
        import lzma
        try:
            input = lzma.LZMAFile(localpath)
            output = open(self.getTargetPath(localpath), "w")
            data = input.read(BLOCKSIZE)
            while data:
                output.write(data)
                data = input.read(BLOCKSIZE)
        except (IOError, OSError), e:
            raise Error, "%s: %s" % (localpath, e)
        except EOFError, e:
            raise Error, ("%s\nPossibly corrupted channel file.") % e

Uncompressor.addHandler(XZHandler)

class GZipHandler(UncompressorHandler):

    def query(self, localpath):
        if localpath.endswith(".gz"):
            return True

    def getTargetPath(self, localpath):
        return localpath[:-3]

    def uncompress(self, localpath):
        import gzip
        try:
            input = gzip.GzipFile(localpath)
            output = open(self.getTargetPath(localpath), "w")
            data = input.read(BLOCKSIZE)
            while data:
                output.write(data)
                data = input.read(BLOCKSIZE)
        except (IOError, OSError), e:
            raise Error, "%s: %s" % (localpath, e)
        except EOFError, e:
            raise Error, ("%s\nPossibly corrupted channel file.") % e

Uncompressor.addHandler(GZipHandler)

class ZipHandler(UncompressorHandler):

    def query(self, localpath):
        if localpath.endswith(".zip"):
            return True

    def getTargetPath(self, localpath, name=None):
        import zipfile
        try:
            zip = zipfile.ZipFile(localpath, 'r')
            members = zip.namelist()
            zip.close()
            if len(members) > 0:
                if not name:
                    name = members[0]
                dir = os.path.dirname(localpath)
                return os.path.join(dir, name)
        except (IOError, OSError), e:
            raise Error, "%s: %s" % (localpath, e)
        return None

    def uncompress(self, localpath, name=None):
        import zipfile
        try:
            zip = zipfile.ZipFile(localpath, 'r')
            members = zip.namelist()
            if not name:
                name = members[0]
            output = open(self.getTargetPath(localpath), "w")
            data = zip.read(name)
            output.write(data)
            zip.close()
        except (IOError, OSError), e:
            raise Error, "%s: %s" % (localpath, e)

Uncompressor.addHandler(ZipHandler)

class SevenZipHandler(UncompressorHandler):

    def query(self, localpath):
        if localpath.endswith(".7z"):
            return True

    def getTargetPath(self, localpath, name=None):
        import py7zlib
        try:
            zip = py7zlib.Archive7z(open(localpath, 'r'))
            members = zip.getnames()
            if len(members) > 0:
                if not name:
                    name = members[0]
                dir = os.path.dirname(localpath)
                return os.path.join(dir, name)
        except (IOError, OSError), e:
            raise Error, "%s: %s" % (localpath, e)
        return None

    def uncompress(self, localpath, name=None):
        import py7zlib
        try:
            zip = py7zlib.Archive7z(open(localpath, 'r'))
            members = zip.getnames()
            if not name:
                name = members[0]
            output = open(self.getTargetPath(localpath), "w")
            input = zip.getmember(name)
            data = input.read()
            output.write(data)
        except (IOError, OSError), e:
            raise Error, "%s: %s" % (localpath, e)

Uncompressor.addHandler(SevenZipHandler)

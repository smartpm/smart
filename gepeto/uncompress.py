from gepeto.const import BLOCKSIZE
from gepeto import *

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
            raise Error, "unknown compressed file: %s" % localpath

class UncompressorHandler(object):

    def query(self, localpath):
        return None

    def getTargetPath(self, localpath):
        return None

    def uncompress(self, localpath):
        raise Error, "unsupported file type"

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

Uncompressor.addHandler(BZ2Handler)

class GZipHandler:

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


Uncompressor.addHandler(GZipHandler)

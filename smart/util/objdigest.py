
import cPickle
import md5

def getObjectDigest(obj):
    return ObjectDigest(obj).getDigest()

def getObjectHexDigest(obj):
    return ObjectDigest(obj).getHexDigest()

class ObjectDigest(object):

    def __init__(self, obj=None):
        self._digest = md5.md5()
        if obj:
            self.addObject(obj)

    def getDigest(self):
        return self._digest.digest()

    def getHexDigest(self):
        return self._digest.hexdigest()
    
    def addObject(self, obj):
        cPickle.dump(obj, DigestFile(self._digest), 2)

class DigestFile(object):

    def __init__(self, digest):
        self._digest = digest

    def write(self, data):
        self._digest.update(data)



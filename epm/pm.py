
class PackageManager:
    def __init__(self):
        self._progress = None

    def setProgress(self, prog):
        self._progress = prog

    def getProgress(self):
        return self._progress

    def commit(self, set, pkgpath):
        pass

# vim:ts=4:sw=4:et

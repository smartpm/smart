from cpm.interfaces.gtk.progress import GtkProgress
from cpm.interfaces.gtk.changes import GtkChanges
from cpm.interfaces.gtk.log import GtkLog
from cpm.interface import Interface
from cpm.fetcher import Fetcher
import gtk

class GtkInterface(Interface):

    def __init__(self):
        self._log = GtkLog()
        self._progress = GtkProgress(False)
        self._hassubprogress = GtkProgress(True)
        self._changes = GtkChanges()

    def getProgress(self, obj, hassub=False):
        if hassub:
            self._progress.hide()
            self._hassubprogress.setFetcherMode(isinstance(obj, Fetcher))
            return self._hassubprogress
        else:
            self._hassubprogress.hide()
            return self._progress

    def getSubProgress(self, obj):
        return self._hassubprogress

    def message(self, level, msg):
        self._log.message(level, msg)

    def confirmChange(self, oldchangeset, newchangeset):
        changeset = newchangeset.difference(oldchangeset)
        keep = []
        for pkg in oldchangeset:
            if pkg not in newchangeset:
                keep.append(pkg)
        if len(keep)+len(changeset) <= 1:
            return True
        return self._changes.showChangeSet(changeset, keep=keep, confirm=True)

    def confirmTransaction(self, trans):
        return self._changes.showChangeSet(trans.getChangeSet(), confirm=True)

    # Non-standard interface methods

    def hideProgress(self):
        self._progress.hide()
        self._hassubprogress.hide()


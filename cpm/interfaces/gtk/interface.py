from cpm.interfaces.gtk.progress import GtkProgress
from cpm.interfaces.gtk.changes import GtkChanges
from cpm.interfaces.gtk.log import GtkLog
from cpm.interface import Interface
import gtk

class GtkInterface(Interface):

    def __init__(self):
        self._log = GtkLog()
        self._progress = GtkProgress()
        self._changes = None

    def getProgress(self, obj, hassub=False):
        self._progress.setHasSub(hassub)
        return self._progress

    def getSubProgress(self, obj):
        return self._progress

    def message(self, level, msg):
        self._log.message(level, msg)

    def confirmChange(self, oldchangeset, newchangeset):
        if not self._changes:
            self._changes = GtkChanges()
        changeset = newchangeset.difference(oldchangeset)
        keep = []
        for pkg in oldchangeset:
            if pkg not in newchangeset:
                keep.append(pkg)
        if len(keep)+len(changeset) <= 1:
            return True
        return self._changes.showChangeSet(changeset, keep=keep, confirm=True)

    def confirmTransaction(self, trans):
        if not self._changes:
            self._changes = GtkChanges()
        return self._changes.showChangeSet(trans.getChangeSet(), confirm=True)

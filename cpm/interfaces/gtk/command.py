from cpm.interfaces.gtk.progress import GtkProgress
from cpm.interfaces.gtk.changes import GtkChanges
from cpm.interfaces.gtk.log import GtkLog
from cpm.interface import Interface
from cpm import *
import time
import gtk

class GtkCommandInterface(Interface):

    def __init__(self):
        self._log = GtkLog()
        self._progress = GtkProgress()
        self._changes = None
        self._status = GtkStatus()

    def getProgress(self, obj, hassub=False):
        self._progress.setHasSub(hassub)
        return self._progress

    def getSubProgress(self, obj):
        return self._progress

    def showStatus(self, msg):
        self._status.show(msg)

    def hideStatus(self):
        self._status.hide()

    def message(self, level, msg):
        self._log.message(level, msg)

    def confirmTransaction(self, trans):
        if not self._changes:
            self._changes = GtkChanges()
        return self._changes.showChangeSet(trans.getCache(),
                                           trans.getChangeSet(),
                                           confirm=True)

    def finish(self):
        self._status.wait()
        while self._log.isVisible():
            time.sleep(0.1)
            while gtk.events_pending():
                gtk.main_iteration()

class GtkStatus:

    def __init__(self):
        self._window = gtk.Window()
        self._window.set_title("Status")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_border_width(20)

        self._label = gtk.Label()
        self._label.show()
        self._window.add(self._label)

        self._lastshown = 0

    def show(self, msg):
        self._label.set_text(msg)
        self._window.show()
        self._lastshown = time.time()

    def hide(self):
        self._window.hide()

    def isVisible(self):
        return self._window.get_property("visible")

    def wait(self):
        while self.isVisible() and self._lastshown+3 > time.time():
            time.sleep(0.3)
            while gtk.events_pending():
                gtk.main_iteration()

# vim:ts=4:sw=4:et

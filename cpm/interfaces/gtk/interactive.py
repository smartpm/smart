from cpm.interfaces.gtk.packageview import GtkPackageView
from cpm.interfaces.gtk.progress import GtkProgress
from cpm.interfaces.gtk.changes import GtkChanges
from cpm.interfaces.gtk.log import GtkLog
from cpm.interface import Interface
from cpm import *
import gtk

class GtkInteractiveInterface(Interface):

    def __init__(self):
        self._ctrl = None

        self._log = GtkLog()
        self._progress = GtkProgress()
        self._changes = None

        self._window = gtk.Window()
        self._window.set_title("")
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=400, min_height=300)
        self._window.connect("destroy", lambda x: gtk.main_quit())

        self._topvbox = gtk.VBox()
        self._topvbox.show()
        self._window.add(self._topvbox)

        self._menubar = gtk.MenuBar()
        self._menubar.show()
        self._topvbox.pack_start(self._menubar, False)

        menuitem = gtk.MenuItem("File")
        submenu = gtk.Menu()
        submenu.show()
        submenuitem = gtk.SeparatorMenuItem()
        submenuitem.show()
        submenu.add(submenuitem)
        submenuitem = gtk.ImageMenuItem(stock_id="gtk-quit")
        submenuitem.connect("activate", lambda x: gtk.main_quit())
        submenuitem.show()
        submenu.add(submenuitem)
        menuitem.set_submenu(submenu)
        menuitem.show()
        self._menubar.add(menuitem)

        self._toolbar = gtk.Toolbar()
        self._toolbar.show()
        self._topvbox.pack_start(self._toolbar, False)

        button = self._toolbar.append_item("Foobar", "Foobar baz",
                                           None, None, None, None)

        self._pv = GtkPackageView()
        self._topvbox.pack_start(self._pv.getScrolledWindow())

        self._status = gtk.Statusbar()
        self._status.show()
        self._topvbox.pack_start(self._status, False)

    def getProgress(self, obj, hassub=False):
        self._progress.setHasSub(hassub)
        return self._progress

    def getSubProgress(self, obj):
        return self._progress

    def showStatus(self, msg):
        self._status.push(msg)

    def hideStatus(self):
        self._status.pop()

    def run(self, ctrl):
        self._ctrl = ctrl
        self._window.show()
        ctrl.fetchRepositories()
        ctrl.loadCache()
        self._progress.hide()
        self._pv.setPackages(ctrl.getCache().getPackages())
        gtk.main()

    def message(self, level, msg):
        self._log.message(level, msg)

    def confirmTransaction(self, trans):
        if not self._changes:
            self._changes = GtkChanges()
        return self._changes.showChangeSet(trans.getCache(),
                                           trans.getChangeSet(),
                                           confirm=True)


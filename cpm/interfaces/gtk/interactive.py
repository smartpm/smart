from cpm.transaction import PolicyInstall, PolicyRemove, PolicyUpgrade
from cpm.transaction import Transaction, INSTALL, REMOVE
from cpm.interfaces.gtk.packageview import GtkPackageView
from cpm.interfaces.gtk.packageinfo import GtkPackageInfo
from cpm.interfaces.gtk.interface import GtkInterface
from cpm.const import NEVER
from cpm import *
import gtk

class GtkInteractiveInterface(GtkInterface):

    def __init__(self):
        GtkInterface.__init__(self)

        self._ctrl = None
        self._transaction = None

        self._window = gtk.Window()
        self._window.set_title("")
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=640, min_height=480)
        self._window.connect("destroy", lambda x: gtk.main_quit())

        self._log.set_transient_for(self._window)
        self._progress.set_transient_for(self._window)
        self._hassubprogress.set_transient_for(self._window)

        self._topvbox = gtk.VBox()
        self._topvbox.show()
        self._window.add(self._topvbox)

        self._menubar = gtk.MenuBar()
        self._menubar.show()
        self._topvbox.pack_start(self._menubar, False)

        menuitem = gtk.MenuItem("_File")
        submenu = gtk.Menu()
        submenu.show()
        submenuitem = gtk.MenuItem("_Update...")
        submenuitem.show()
        submenu.add(submenuitem)
        submenuitem = gtk.MenuItem("Update _All")
        submenuitem.connect("activate", lambda x: self.updateAll())
        submenuitem.show()
        submenu.add(submenuitem)
        submenuitem = gtk.SeparatorMenuItem()
        submenuitem.show()
        submenu.add(submenuitem)
        submenuitem = gtk.MenuItem("Apply _Changes...")
        submenuitem.connect("activate", lambda x: self.applyChanges())
        submenuitem.show()
        submenu.add(submenuitem)
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

        menuitem = gtk.MenuItem("_Edit")
        submenu = gtk.Menu()
        submenu.show()
        submenuitem = gtk.MenuItem("_Channels...")
        submenuitem.show()
        submenu.add(submenuitem)
        submenuitem = gtk.SeparatorMenuItem()
        submenuitem.show()
        submenu.add(submenuitem)
        submenuitem = gtk.ImageMenuItem(stock_id="gtk-preferences")
        submenuitem.show()
        submenu.add(submenuitem)
        menuitem.set_submenu(submenu)
        menuitem.show()
        self._menubar.add(menuitem)

        menuitem = gtk.MenuItem("_View")
        submenu = gtk.Menu()
        submenu.show()
        submenuitem = gtk.MenuItem("_Log Window")
        submenuitem.connect("activate", lambda x: self._log.show())
        submenuitem.show()
        submenu.add(submenuitem)
        submenuitem = gtk.SeparatorMenuItem()
        submenuitem.show()
        submenu.add(submenuitem)

        submenuitem = gtk.MenuItem("Filter")
        submenuitem.show()
        filters = sysconf.get("package-filters", {})
        subsubmenu = gtk.Menu()
        subsubmenuitem = None
        for label, filter in [("Hide Installed", "hide-installed"),
                              ("Hide Uninstalled", "hide-uninstalled"),
                              ("Hide Marked", "hide-marked"),
                              ("Hide Unmarked", "hide-unmarked")]:
            subsubmenuitem = gtk.CheckMenuItem(label)
            if filter in filters:
                subsubmenuitem.set_active(True)
            subsubmenuitem.connect("toggled",
                                   lambda x, y: self.togglePackageFilter(y),
                                   filter)
            subsubmenuitem.show()
            subsubmenu.add(subsubmenuitem)
        submenuitem.set_submenu(subsubmenu)
        submenu.add(submenuitem)

        submenuitem = gtk.MenuItem("Tree Style")
        submenuitem.show()
        tree = sysconf.get("package-tree", "groups")
        subsubmenu = gtk.Menu()
        subsubmenuitem = None
        for label, mode in [("Groups", "groups"),
                            ("Channels", "channels"),
                            ("Channels & Groups", "channels-groups"),
                            ("None", "none")]:
            subsubmenuitem = gtk.RadioMenuItem(subsubmenuitem, label)
            if tree == mode:
                subsubmenuitem.set_active(True)
            subsubmenuitem.connect("activate",
                                   lambda x, y: x.get_active() and
                                                self.setPackageTree(y), mode)
            subsubmenuitem.show()
            subsubmenu.add(subsubmenuitem)
        submenuitem.set_submenu(subsubmenu)
        submenu.add(submenuitem)

        menuitem.set_submenu(submenu)
        menuitem.show()
        self._menubar.add(menuitem)

        self._toolbar = gtk.Toolbar()
        self._toolbar.show()
        self._topvbox.pack_start(self._toolbar, False)

        button = self._toolbar.append_item("Foobar", "Foobar baz",
                                           None, None, None, None)

        self._vpaned = gtk.VPaned()
        self._vpaned.show()
        self._topvbox.pack_start(self._vpaned)

        self._pv = GtkPackageView()
        self._pv.show()
        self._vpaned.pack1(self._pv, True)

        self._pi = GtkPackageInfo()
        self._pi.show()
        self._pv.connect("package_selected",
                         lambda x, y: self._pi.setPackage(y))
        self._pv.connect("package_activated",
                         lambda x, y: self.togglePackage(y))
        self._vpaned.pack2(self._pi, False)

        self._status = gtk.Statusbar()
        self._status.show()
        self._topvbox.pack_start(self._status, False)

    def showStatus(self, msg):
        self._status.pop(0)
        self._status.push(0, msg)

    def hideStatus(self):
        self._status.pop(0)

    def run(self, ctrl):
        self._ctrl = ctrl
        self._transaction = Transaction(ctrl.getCache())
        self._window.show()
        ctrl.fetchChannels()
        ctrl.loadCache()
        self._progress.hide()
        self.refreshPackages()
        gtk.main()

    # Non-standard interface methods:

    def getTransaction(self):
        return self._transaction

    def updateAll(self):
        self._ctrl.unloadCache()
        self._ctrl.fetchChannels(caching=NEVER)
        self._ctrl.loadCache()
        self.refreshPackages()
        self._progress.hide()

    def applyChanges(self):
        if self._ctrl.commitTransaction(self._transaction):
            self._transaction.getChangeSet().clear()
            self._ctrl.unloadCache()
            self._ctrl.fetchChannels()
            self._ctrl.loadCache()
            self.refreshPackages()
        self._progress.hide()

    def togglePackageFilter(self, filter):
        filters = sysconf.get("package-filters", {})
        if filter in filters:
            del filters[filter]
        else:
            filters[filter] = True
        sysconf.set("package-filters", filters)
        self.refreshPackages()

    def togglePackage(self, pkg):
        transaction = self._transaction
        oldchangeset = transaction.getChangeSet()
        newchangeset = oldchangeset.copy()
        transaction.setChangeSet(newchangeset)
        if pkg.installed:
            if oldchangeset.get(pkg) is REMOVE:
                policy = PolicyInstall
                transaction.enqueue(pkg, INSTALL)
            else:
                policy = PolicyRemove
                transaction.enqueue(pkg, REMOVE)
        else:
            if oldchangeset.get(pkg) is INSTALL:
                policy = PolicyRemove
                transaction.enqueue(pkg, REMOVE)
            else:
                policy = PolicyInstall
                transaction.enqueue(pkg, INSTALL)
        transaction.setPolicy(policy)
        try:
            transaction.run()
        except Error, e:
            self.error(str(e[0]))
        else:
            if self.confirmChange(oldchangeset, newchangeset):
                oldchangeset.setState(newchangeset)
                self._pv.queue_draw()
        transaction.setChangeSet(oldchangeset)

    def setPackageTree(self, mode):
        if mode != sysconf.get("package-tree"):
            sysconf.set("package-tree", mode)
            self.refreshPackages()

    def refreshPackages(self):
        if not self._ctrl:
            return

        tree = sysconf.get("package-tree", "groups")
        ctrl = self._ctrl
        packages = ctrl.getCache().getPackages()

        filters = sysconf.get("package-filters", {})

        if filters:
            if "hide-installed" in filters:
                packages = [x for x in packages if not x.installed]
            if "hide-uninstalled" in filters:
                packages = [x for x in packages if x.installed]
            if "hide-marked" in filters:
                pass
            if "hide-unmarked" in filters:
                pass

        if tree == "groups":
            groups = {}
            done = {}
            for pkg in packages:
                lastgroup = None
                for loader in pkg.loaders:
                    info = loader.getInfo(pkg)
                    group = info.getGroup()
                    donetuple = (group, pkg)
                    if donetuple not in done:
                        done[donetuple] = True
                        if group in groups:
                            groups[group].append(pkg)
                        else:
                            groups[group] = [pkg]

        elif tree == "channels":
            groups = {}
            done = {}
            for pkg in packages:
                for loader in pkg.loaders:
                    group = loader.getChannel().getName()
                    donetuple = (group, pkg)
                    if donetuple not in done:
                        done[donetuple] = True
                        if group in groups:
                            groups[group].append(pkg)
                        else:
                            groups[group] = [pkg]

        elif tree == "channels-groups":
            groups = {}
            done = {}
            for pkg in packages:
                for loader in pkg.loaders:
                    group = loader.getChannel().getName()
                    subgroup = loader.getInfo(pkg).getGroup()
                    donetuple = (group, subgroup, pkg)
                    if donetuple not in done:
                        done[donetuple] = True
                        if group in groups:
                            if subgroup in groups[group]:
                                groups[group][subgroup].append(pkg)
                            else:
                                groups[group][subgroup] = [pkg]
                        else:
                            groups[group] = {subgroup: [pkg]}

        else:
            groups = packages

        self._pv.setPackages(groups, self._transaction.getChangeSet())

        if filters:
            self.showStatus("There are filters being applied!")
        else:
            self.hideStatus()

# vim:ts=4:sw=4:et

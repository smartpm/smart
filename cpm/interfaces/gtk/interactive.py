from cpm.interfaces.gtk.packageview import GtkPackageView
from cpm.interfaces.gtk.packageinfo import GtkPackageInfo
from cpm.interfaces.gtk.progress import GtkProgress
from cpm.interfaces.gtk.changes import GtkChanges
from cpm.interfaces.gtk.log import GtkLog
from cpm.interface import Interface
from cpm import *
import gtk

class GtkInteractiveInterface(Interface):

    def __init__(self):
        self._ctrl = None

        self._window = gtk.Window()

        self._log = GtkLog()
        self._progress = GtkProgress(self._window)
        self._changes = None

        self._window.set_title("")
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=640, min_height=480)
        self._window.connect("destroy", lambda x: gtk.main_quit())

        self._topvbox = gtk.VBox()
        self._topvbox.show()
        self._window.add(self._topvbox)

        self._menubar = gtk.MenuBar()
        self._menubar.show()
        self._topvbox.pack_start(self._menubar, False)

        menuitem = gtk.MenuItem("_File")
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

        menuitem = gtk.MenuItem("_Edit")
        submenu = gtk.Menu()
        submenu.show()
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
        submenuitem = gtk.SeparatorMenuItem()
        submenuitem.show()
        submenu.add(submenuitem)

        submenuitem = gtk.MenuItem("Filter")
        submenuitem.show()
        def toggle_package_filter(item, filter):
            filters = sysconf.get("package-filters", {})
            if filter in filters:
                del filters[filter]
            else:
                filters[filter] = True
            sysconf.set("package-filters", filters)
            self.refreshPackages()
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
            subsubmenuitem.connect("toggled", toggle_package_filter, filter)
            subsubmenuitem.show()
            subsubmenu.add(subsubmenuitem)
        submenuitem.set_submenu(subsubmenu)
        submenu.add(submenuitem)

        submenuitem = gtk.MenuItem("Tree Style")
        submenuitem.show()
        def set_package_tree(item, mode):
            if item.get_active() and mode != sysconf.get("package-tree"):
                sysconf.set("package-tree", mode)
                self.refreshPackages()
        tree = sysconf.get("package-tree", "groups")
        subsubmenu = gtk.Menu()
        subsubmenuitem = None
        for label, mode in [("Groups", "groups"),
                            ("Repositories", "repositories"),
                            ("Repositories & Groups", "repositories-groups"),
                            ("None", "none")]:
            subsubmenuitem = gtk.RadioMenuItem(subsubmenuitem, label)
            if tree == mode:
                subsubmenuitem.set_active(True)
            subsubmenuitem.connect("activate", set_package_tree, mode)
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
        self._vpaned.pack1(self._pv.getTopWidget(), True)

        self._pi = GtkPackageInfo()
        self._pv.connect("package_selected",
                         lambda x, y: self._pi.setPackage(y))
        self._vpaned.pack2(self._pi.getTopWidget(), False)

        self._status = gtk.Statusbar()
        self._status.show()
        self._topvbox.pack_start(self._status, False)

    def getProgress(self, obj, hassub=False):
        self._progress.setHasSub(hassub)
        return self._progress

    def getSubProgress(self, obj):
        return self._progress

    def showStatus(self, msg):
        self._status.pop(0)
        self._status.push(0, msg)

    def hideStatus(self):
        self._status.pop(0)

    def run(self, ctrl):
        self._ctrl = ctrl
        self._window.show()
        ctrl.fetchRepositories()
        ctrl.loadCache()
        self._progress.hide()
        self.refreshPackages()
        gtk.main()

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

        elif tree == "repositories":
            groups = {}
            done = {}
            for pkg in packages:
                for loader in pkg.loaders:
                    group = loader.getRepository().getName()
                    donetuple = (group, pkg)
                    if donetuple not in done:
                        done[donetuple] = True
                        if group in groups:
                            groups[group].append(pkg)
                        else:
                            groups[group] = [pkg]

        elif tree == "repositories-groups":
            groups = {}
            done = {}
            for pkg in packages:
                for loader in pkg.loaders:
                    group = loader.getRepository().getName()
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

        self._pv.setPackages(groups)

        if filters:
            self.showStatus("There are filters being applied!")
        else:
            self.hideStatus()

    def message(self, level, msg):
        self._log.message(level, msg)

    def confirmTransaction(self, trans):
        if not self._changes:
            self._changes = GtkChanges()
        return self._changes.showChangeSet(trans.getCache(),
                                           trans.getChangeSet(),
                                           confirm=True)


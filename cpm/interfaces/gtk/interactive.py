from cpm.transaction import Transaction, ChangeSet, INSTALL, REMOVE, UPGRADE
from cpm.transaction import PolicyInstall, PolicyRemove, PolicyUpgrade
from cpm.interfaces.gtk.packageview import GtkPackageView
from cpm.interfaces.gtk.packageinfo import GtkPackageInfo
from cpm.interfaces.gtk.interface import GtkInterface
from cpm.const import NEVER
from cpm import *
import gtk

UI = """
<ui>
<menubar>
    <menu action="file">
        <menuitem action="update-channels"/>
        <menuitem action="update-all-channels"/>
        <separator/>
        <menuitem action="exec-changes"/>
        <separator/>
        <menuitem action="quit"/>
    </menu>
    <menu action="edit">
        <menuitem action="undo"/>
        <menuitem action="redo"/>
        <menuitem action="clear-changes"/>
        <separator/>
        <menuitem action="upgrade-all"/>
        <separator/>
        <menuitem action="edit-channels"/>
        <menuitem action="edit-preferences"/>
    </menu>
    <menu action="view">
        <menuitem action="show-upgrades"/>
        <menuitem action="hide-installed"/>
        <menuitem action="hide-uninstalled"/>
        <menuitem action="hide-unmarked"/>
        <separator/>
        <menuitem action="expand-all"/>
        <menuitem action="collapse-all"/>
        <separator/>
        <menu action="tree-style">
            <menuitem action="tree-style-groups"/>
            <menuitem action="tree-style-channels"/>
            <menuitem action="tree-style-channels-groups"/>
            <menuitem action="tree-style-none"/>
        </menu>
        <separator/>
        <menuitem action="summary-window"/>
        <menuitem action="log-window"/>
    </menu>
</menubar>
</ui>
"""

ACTIONS = [
    ("file", None, "_File"),
    ("update-channels", "gtk-refresh", "Update Channels...", None,
     "Update given channels", "self.updateChannels()"),
    ("update-all-channels", "gtk-refresh", "Update All Channels", None,
     "Update given channels", "self.updateChannels()"),
    ("exec-changes", "gtk-execute", "Execute Changes...", "<control>c",
     "Apply marked changes", "self.applyChanges()"),
    ("quit", "gtk-quit", "_Quit", "<control>q",
     "Quit application", "gtk.main_quit()"),

    ("edit", None, "_Edit"),
    ("undo", "gtk-undo", "_Undo", "<control>z",
     "Undo last change", "self.undo()"),
    ("redo", "gtk-redo", "_Redo", "<control><shift>z",
     "Redo last undone change", "self.redo()"),
    ("clear-changes", "gtk-clear", "Clear Changes", None,
     "Clear all changes", "self.clearChanges()"),
    ("upgrade-all", "gtk-go-up", "Upgrade All...", None,
     "Upgrade all packages", "self.upgradeAll()"),
    ("edit-channels", None, "Channels", None,
     "Edit channels", ""),
    ("edit-preferences", "gtk-preferences", "_Preferences", None,
     "Edit preferences", ""),

    ("view", None, "_View"),
    ("tree-style", None, "Tree Style"),
    ("expand-all", "gtk-open", "Expand All", None,
     "Expand all items in the tree", "self._pv.getTreeView().expand_all()"),
    ("collapse-all", "gtk-close", "Collapse All", None,
     "Collapse all items in the tree", "self._pv.getTreeView().collapse_all()"),
    ("summary-window", None, "Summary Window", "<control>s",
     "Show summary window", "self.showChanges()"),
    ("log-window", None, "Log Window", None,
     "Show log window", "self._log.show()"),
]

def compileActions(actions, globals):
    newactions = []
    for action in actions:
        if len(action) > 5:
            action = list(action)
            code = compile(action[5], "<callback>", "exec")
            def callback(action, code=code, globals=globals):
                globals["action"] = action
                exec code in globals
            action[5] = callback
        newactions.append(tuple(action))
    return newactions

class GtkInteractiveInterface(GtkInterface):

    def __init__(self):
        GtkInterface.__init__(self)

        self._ctrl = None
        self._changeset = None

        self._window = gtk.Window()
        self._window.set_title("")
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=640, min_height=480)
        self._window.connect("destroy", lambda x: gtk.main_quit())

        self._log.set_transient_for(self._window)
        self._progress.set_transient_for(self._window)
        self._hassubprogress.set_transient_for(self._window)

        self._watch = gtk.gdk.Cursor(gtk.gdk.WATCH)

        self._undo = []
        self._redo = []

        self._topvbox = gtk.VBox()
        self._topvbox.show()
        self._window.add(self._topvbox)

        globals = {"self": self, "gtk": gtk}
        self._actions = gtk.ActionGroup("Actions")
        self._actions.add_actions(compileActions(ACTIONS, globals))

        filters = sysconf.get("package-filters", {})
        for name, label in [("show-upgrades", "Show Upgrades"),
                            ("hide-installed", "Hide Installed"),
                            ("hide-uninstalled", "Hide Uninstalled"),
                            ("hide-unmarked", "Hide Unmarked")]:
            action = gtk.ToggleAction(name, label, "", "")
            if name in filters:
                action.set_active(True)
            action.connect("toggled", lambda x, y: self.toggleFilter(y), name)
            self._actions.add_action(action)

        treestyle = sysconf.get("package-tree", {})
        lastaction = None
        for name, label in [("groups", "Groups"),
                            ("channels", "Channels"),
                            ("channels-groups", "Channels & Groups"),
                            ("none", "None")]:
            action = gtk.RadioAction("tree-style-"+name, label, "", "", 0)
            if name == treestyle:
                action.set_active(True)
            if lastaction:
                action.set_group(lastaction)
            lastaction = action
            action.connect("toggled", lambda x, y: self.setTreeStyle(y), name)
            self._actions.add_action(action)

        self._ui = gtk.UIManager()
        self._ui.insert_action_group(self._actions, 0)
        self._ui.add_ui_from_string(UI)
        self._menubar = self._ui.get_widget("/menubar")
        self._topvbox.pack_start(self._menubar, False)

        self._window.add_accel_group(self._ui.get_accel_group())

        self._undomenuitem = self._ui.get_widget("/menubar/edit/undo")
        self._undomenuitem.set_sensitive(False)
        self._redomenuitem = self._ui.get_widget("/menubar/edit/redo")
        self._redomenuitem.set_sensitive(False)

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
        self._changeset = ChangeSet(ctrl.getCache())
        self._window.show()
        ctrl.updateCache()
        self._progress.hide()
        self.refreshPackages()
        gtk.main()

    # Non-standard interface methods:

    def getChangeSet(self):
        return self._changeset

    def updateChannels(self):
        pass

    def updateAllChannels(self):
        state = self._changeset.getPersistentState()
        self._ctrl.updateCache(caching=NEVER)
        self._changeset.setPersistentState(state)
        self.refreshPackages()
        self._progress.hide()

    def applyChanges(self):
        transaction = Transaction(self._ctrl.getCache(),
                                  changeset=self._changeset)
        if self._ctrl.commitTransaction(transaction):
            del self._undo[:]
            del self._redo[:]
            self._changeset.clear()
            self._ctrl.updateCache()
            self.refreshPackages()
        self._progress.hide()

    def clearChanges(self):
        self.saveUndo()
        self._changeset.clear()
        self.changedMarks()

    def showChanges(self):
        return self._changes.showChangeSet(self._changeset)

    def toggleFilter(self, filter):
        filters = sysconf.get("package-filters", {})
        if filter in filters:
            del filters[filter]
        else:
            filters[filter] = True
        sysconf.set("package-filters", filters)
        self.refreshPackages()

    def upgradeAll(self):
        transaction = Transaction(self._ctrl.getCache())
        transaction.setState(self._changeset)
        for pkg in self._ctrl.getCache().getPackages():
            if pkg.installed:
                transaction.enqueue(pkg, UPGRADE)
        transaction.setPolicy(PolicyUpgrade)
        try:
            transaction.run()
        except Error, e:
            self.error(str(e[0]))
        else:
            changeset = transaction.getChangeSet()
            if self.confirmChange(self._changeset, changeset):
                self.saveUndo()
                self._changeset.setState(changeset)
                self.changedMarks()

    def togglePackage(self, pkg):
        transaction = Transaction(self._ctrl.getCache(), policy=PolicyInstall)
        transaction.setState(self._changeset)
        if pkg.installed:
            if self._changeset.get(pkg) is REMOVE:
                transaction.enqueue(pkg, INSTALL)
            else:
                transaction.setPolicy(PolicyRemove)
                transaction.enqueue(pkg, REMOVE)
        else:
            if self._changeset.get(pkg) is INSTALL:
                transaction.enqueue(pkg, REMOVE)
            else:
                transaction.enqueue(pkg, INSTALL)
        try:
            transaction.run()
        except Error, e:
            self.error(str(e[0]))
        else:
            changeset = transaction.getChangeSet()
            if self.confirmChange(self._changeset, changeset):
                self.saveUndo()
                self._changeset.setState(changeset)
                self.changedMarks()

    def undo(self):
        if self._undo:
            state = self._undo.pop(0)
            if not self._undo:
                self._undomenuitem.set_sensitive(False)
            self._redo.insert(0, self._changeset.getPersistentState())
            self._redomenuitem.set_sensitive(True)
            self._changeset.setPersistentState(state)
            self.changedMarks()

    def redo(self):
        if self._redo:
            state = self._redo.pop(0)
            if not self._redo:
                self._redomenuitem.set_sensitive(False)
            self._undo.insert(0, self._changeset.getPersistentState())
            self._undomenuitem.set_sensitive(True)
            self._changeset.setPersistentState(state)
            self.changedMarks()

    def saveUndo(self):
        self._undo.insert(0, self._changeset.getPersistentState())
        del self._redo[:]
        del self._undo[20:]
        self._undomenuitem.set_sensitive(True)
        self._redomenuitem.set_sensitive(False)

    def setTreeStyle(self, mode):
        if mode != sysconf.get("package-tree"):
            sysconf.set("package-tree", mode)
            self.refreshPackages()

    def setBusy(self, flag):
        if flag:
            self._window.window.set_cursor(self._watch)
            while gtk.events_pending():
                gtk.main_iteration()
        else:
            self._window.window.set_cursor(None)

    def changedMarks(self):
        if "hide-unmarked" in sysconf.get("package-filters", {}):
            self.refreshPackages()
        else:
            self._pv.queue_draw()

    def refreshPackages(self):
        if not self._ctrl:
            return

        self.setBusy(True)

        tree = sysconf.get("package-tree", "groups")
        ctrl = self._ctrl
        packages = ctrl.getCache().getPackages()

        filters = sysconf.get("package-filters", {})

        changeset = self._changeset

        if filters:
            if "show-upgrades" in filters:
                newpackages = {}
                for pkg in packages:
                    if pkg.installed:
                        upgpkgs = {}
                        try:
                            for prv in pkg.provides:
                                for upg in prv.upgradedby:
                                    for upgpkg in upg.packages:
                                        if upgpkg.installed:
                                            raise StopIteration
                                        upgpkgs[upgpkg] = True
                        except StopIteration:
                            pass
                        else:
                            newpackages.update(upgpkgs)
                packages = newpackages.keys()
            if "hide-uninstalled" in filters:
                packages = [x for x in packages if x.installed]
            if "hide-unmarked" in filters:
                packages = [x for x in packages if x in changeset]
            if "hide-installed" in filters:
                packages = [x for x in packages if not x.installed]

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

        self._pv.setPackages(groups, changeset, keepstate=True)

        if filters:
            self.showStatus("There are filters being applied!")
        else:
            self.hideStatus()

        self.setBusy(False)


# vim:ts=4:sw=4:et

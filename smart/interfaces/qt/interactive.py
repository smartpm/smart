#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Anders F Bjorklund <afb@users.sourceforge.net>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from smart.transaction import INSTALL, REMOVE, UPGRADE, REINSTALL, KEEP, FIX
from smart.transaction import Transaction, ChangeSet, checkPackagesSimple
from smart.transaction import PolicyInstall, PolicyRemove, PolicyUpgrade
'''
from smart.interfaces.gtk.channels import GtkChannels, GtkChannelSelector
from smart.interfaces.gtk.mirrors import GtkMirrors
from smart.interfaces.gtk.flags import GtkFlags
from smart.interfaces.gtk.priorities import GtkPriorities, GtkSinglePriority
'''
from smart.interfaces.qt.packageview import QtPackageView
from smart.interfaces.qt.packageinfo import QtPackageInfo
from smart.interfaces.qt.interface import QtInterface, app
from smart.interfaces.qt import getPixmap, centerWindow
from smart.const import NEVER, VERSION
from smart.searcher import Searcher
from smart.cache import Package
from smart import *
import shlex, re
import fnmatch
import qt

MENUBAR = [
    ( "file", [
        "update-selected-channels",
        "update-channels",
        None,
        "rebuild-cache",
        None,
        "exec-changes",
        None,
        "quit"
    ] ),
    ( "edit", [
        "undo",
        "redo",
        "clear-changes",
        None,
        "upgrade-all",
        "fix-all-problems",
        None,
        "check-installed-packages",
        "check-uninstalled-packages",
        "check-all-packages",
        None,
        "find",
        None,
        "edit-channels",
        "edit-mirrors",
        "edit-flags",
        "edit-priorities"
    ] ),
    ( "view", [
        "hide-non-upgrades",
        "hide-installed",
        "hide-uninstalled",
        "hide-unmarked",
        "hide-old",
        None,
        "expand-all",
        "collapse-all",
        None,
        ( "tree-style", [
            "tree-style-groups",
            "tree-style-channels",
            "tree-style-channels-groups",
            "tree-style-none",
        ] ),
        None,
        "summary-window",
        "log-window"
    ] ),
   ( "help", [
        "about",
    ] )
]
TOOLBAR = [
    "update-channels",
    None,
    "exec-changes",
    None,
    "undo",
    "redo",
    "clear-changes",
    None,
    "upgrade-all",
    None,
    "find"
]
TOOLBARICONS = {
    "update-channels": "crystal-reload",
    "upgrade-all": "crystal-upgrade",
    "exec-changes": "crystal-apply",
    "clear-changes": "crystal-trash",
    "undo": "crystal-undo",
    "redo": "crystal-redo",
    "find": "crystal-search",
}

ACTIONS = [
    ("file", None, _("_File")),
    ("update-selected-channels", "gtk-refresh", _("Update _Selected Channels..."), None,
     _("Update given channels"), "self.updateChannels(True)"),
    ("update-channels", "gtk-refresh", _("_Update Channels"), None,
     _("Update channels information"), "self.updateChannels()"),
    ("rebuild-cache", None, _("_Rebuild Cache"), None,
     _("Reload package information"), "self.rebuildCache()"),
    ("exec-changes", "gtk-execute", _("_Execute Changes..."), "<control>c",
     _("Apply marked changes"), "self.applyChanges()"),
    ("quit", "gtk-quit", _("_Quit"), "<control>q",
     _("Quit application"), "gtk.main_quit()"),

    ("edit", None, _("_Edit")),
    ("undo", "gtk-undo", _("_Undo"), "<control>z",
     _("Undo last change"), "self.undo()"),
    ("redo", "gtk-redo", _("_Redo"), "<control><shift>z",
     _("Redo last undone change"), "self.redo()"),
    ("clear-changes", "gtk-clear", _("Clear Marked Changes"), None,
     _("Clear all changes"), "self.clearChanges()"),
    ("check-installed-packages", None, _("Check Installed Packages..."), None,
     _("Check installed packages"), "self.checkPackages()"),
    ("check-uninstalled-packages", None, _("Check Uninstalled Packages..."), None,
     _("Check uninstalled packages"), "self.checkPackages(uninstalled=True)"),
    ("check-all-packages", None, _("Check All Packages..."), None,
     _("Check all packages"), "self.checkPackages(all=True)"),
    ("upgrade-all", "gtk-go-up", _("Upgrade _All..."), None,
     _("Upgrade all packages"), "self.upgradeAll()"),
    ("fix-all-problems", None, _("Fix All _Problems..."), None,
     _("Fix all problems"), "self.fixAllProblems()"),
    ("find", "gtk-find", _("_Find..."), "<control>f",
     _("Find packages"), "self.toggleSearch()"),
    ("edit-channels", None, _("_Channels"), None,
     _("Edit channels"), "self.editChannels()"),
    ("edit-mirrors", None, _("_Mirrors"), None,
     _("Edit mirrors"), "self.editMirrors()"),
    ("edit-flags", None, _("_Flags"), None,
     _("Edit package flags"), "self.editFlags()"),
    ("edit-priorities", None, _("_Priorities"), None,
     _("Edit package priorities"), "self.editPriorities()"),

    ("view", None, _("_View")),
    ("tree-style", None, _("_Tree Style")),
    ("expand-all", "gtk-open", _("_Expand All"), None,
     _("Expand all items in the tree"), "self._pv.getTreeView().expand_all()"),
    ("collapse-all", "gtk-close", _("_Collapse All"), None,
     _("Collapse all items in the tree"), "self._pv.getTreeView().collapse_all()"),
    ("summary-window", None, _("_Summary Window"), "<control>s",
     _("Show summary window"), "self.showChanges()"),
    ("log-window", None, _("_Log Window"), None,
     _("Show log window"), "self._log.show()"),

    ("help", None, _("_Help")),
    ("about", None, _("_About"), None,
     _("Show about window"), "self.showAbout()"),
]

def compileActions(group, actions, globals):
    newactions = {}
    for action in actions:
        #if len(action) > 5:
        #    action = list(action)
        #    code = compile(action[5], "<callback>", "exec")
        #    def callback(action, code=code, globals=globals):
        #        globals["action"] = action
        #        exec code in globals
        #    action[5] = callback
        act = qt.QAction(group, action[0])
        act.setText(action[0])
        act.setMenuText(action[2].replace("_","&"))
        if len(action) > 4:
            act.setToolTip(action[4])
        if len(action) > 5 and type(action[5]) is not str:
            qt.QObject.connect(act, qt.SIGNAL("activated()") , action[5])
        if action[0] == "find": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.toggleSearch)
        if action[0] == "update-channels": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.updateChannels)
        if action[0] == "rebuild-cache": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.rebuildCache)
        if action[0] == "upgrade-all": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.upgradeAll)
        if action[0] == "exec-changes": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.applyChanges)
        if action[0] == "clear-changes": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.clearChanges)
        if action[0] == "expand-all": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.expandPackages)
        if action[0] == "collapse-all": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.collapsePackages)
        if action[0] == "summary-window": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.showChanges)
        if action[0] == "log-window": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.showLog)
        if action[0] == "about": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), self.showAbout)
        if action[0] == "quit": #HACK
            self = globals["self"]
            qt.QObject.connect(act, qt.SIGNAL("activated()"), app, qt.SLOT("quit()"))
        group.add(act)
        #newactions[action[0]] = tuple(action)
        newactions[action[0]] = act
    return newactions

class QtInteractiveInterface(QtInterface):

    def __init__(self, ctrl, argv=None):
        QtInterface.__init__(self, ctrl, argv)

        self._changeset = None

        self._window = qt.QMainWindow()
        self._window.setCaption("Smart Package Manager %s" % VERSION)
        centerWindow(self._window)
        self._window.setMinimumSize(640, 480)
        app.connect(app, qt.SIGNAL('lastWindowClosed()'), app, qt.SLOT('quit()'))

        #self._log.set_transient_for(self._window)
        #self._progress.set_transient_for(self._window)
        #self._hassubprogress.set_transient_for(self._window)
        #self._changes.set_transient_for(self._window)

        #self._watch = gtk.gdk.Cursor(gtk.gdk.WATCH)

        self._undo = []
        self._redo = []

        #self._topvbox = gtk.VBox()
        #self._topvbox.show()
        #self._window.add(self._topvbox)

        globals = {"self": self, "qt": qt}
        #self._actions = gtk.ActionGroup("Actions")
        #self._actions.add_actions(compileActions(ACTIONS, globals))
        group = qt.QActionGroup(self._window, "Actions")
        self._actions = compileActions(group, ACTIONS, globals)

        class ToggleAction(qt.QAction):
        
            def __init__(self, group, name, label):
                qt.QAction.__init__(self, group, name)
                self.setToggleAction(True)
                self.setMenuText(label.replace("&","&&"))
                self._name = name
            
            def connect(self, signal, callback, userdata):
                self._callback = callback
                self._userdata = userdata
                qt.QObject.connect(self, qt.SIGNAL(signal), self.slot)
            
            def slot(self):
                self._callback(self._userdata)
         
        self._filters = {}
        for name, label in [("hide-non-upgrades", _("Hide Non-upgrades")),
                            ("hide-installed", _("Hide Installed")),
                            ("hide-uninstalled", _("Hide Uninstalled")),
                            ("hide-unmarked", _("Hide Unmarked")),
                            ("hide-old", _("Hide Old"))]:
            #action = gtk.ToggleAction(name, label, "", "")
            #action.connect("toggled", lambda x, y: self.toggleFilter(y), name)
            #self._actions.add_action(action)
            act = ToggleAction(None, name, label)
            act.connect("activated()", self.toggleFilter, name)
            self._actions[name] = act

        treestyle = sysconf.get("package-tree")
        #lastaction = None
        for name, label in [("groups", _("Groups")),
                            ("channels", _("Channels")),
                            ("channels-groups", _("Channels & Groups")),
                            ("none", _("None"))]:
            #action = gtk.RadioAction("tree-style-"+name, label, "", "", 0)
            #if name == treestyle:
            #    action.set_active(True)
            #if lastaction:
            #    action.set_group(lastaction)
            #lastaction = action
            #action.connect("toggled", lambda x, y: self.setTreeStyle(y), name)
            #self._actions.add_action(action)
            act = ToggleAction(group, "tree-style-"+name, label)
            if name == treestyle:
                act.setOn(True)
            act.connect("activated()", self.setTreeStyle, name)
            self._actions["tree-style-"+name] = act

        self._menubar = self._window.menuBar()
        for MENU in MENUBAR:
             def insertmenu(menubar, menu):
                item = menu[0]
                action = self._actions[item]
                m = qt.QPopupMenu(menubar)
                text = action.menuText()
                menubar.insertItem(text, m)
                for item in menu[1]:
                    if isinstance(item, tuple):
                        insertmenu(m, item)
                    elif item:
                        action = self._actions[item]
                        #i = qt.QPopupMenu(m)
                        #text = action.menuText()
                        #m.insertItem(text, i)
                        action.addTo(m)
                    else:
                        m.insertSeparator()
             insertmenu(self._menubar, MENU)

        # disable these until the qt dialogs are ready :
        self._actions["edit-channels"].setEnabled(False)
        self._actions["edit-mirrors"].setEnabled(False)
        self._actions["edit-flags"].setEnabled(False)
        self._actions["edit-priorities"].setEnabled(False)

        self._toolbar = qt.QToolBar(self._window)
        for TOOL in TOOLBAR:
            def inserttool(toolbar, tool):
                if tool:
                    action = self._actions[tool]
                    #b = qt.QToolButton(toolbar, TOOL)
                    #b.setTextLabel(action.toolTip())
                    pixmap = getPixmap(TOOLBARICONS[tool])
                    #b.setIconSet(qt.QIconSet(pixmap))
                    action.setIconSet(qt.QIconSet(pixmap))
                    action.addTo(toolbar)
                else:
                    toolbar.addSeparator()
            inserttool(self._toolbar, TOOL)

        #self._window.add_accel_group(self._ui.get_accel_group())

        self._actions["exec-changes"].setEnabled(False)
        self._actions["clear-changes"].setEnabled(False)
        self._actions["undo"].setEnabled(False)
        self._actions["redo"].setEnabled(False)

        # Search bar

        #self._searchbar = gtk.Alignment()
        #self._searchbar.set(0, 0, 1, 1)
        #self._searchbar.set_padding(3, 3, 0, 0)
        #self._topvbox.pack_start(self._searchbar, False)
        self._searchbar = qt.QToolBar(self._window)
        self._searchbar.hide()
       
        #searchvp = gtk.Viewport()
        #searchvp.set_shadow_type(gtk.SHADOW_OUT)
        #searchvp.show()
        #self._searchbar.add(searchvp)

        #searchtable = gtk.Table(1, 1)
        #searchtable.set_row_spacings(5)
        #searchtable.set_col_spacings(5)
        #searchtable.set_border_width(5)
        #searchtable.show()
        #searchvp.add(searchtable)

        #label = gtk.Label(_("Search:"))
        #label.show()
        #searchtable.attach(label, 0, 1, 0, 1, 0, 0)
        label = qt.QLabel(_("Search:"), self._searchbar)
        label.show()

        #self._searchentry = gtk.Entry()
        #self._searchentry.connect("activate", lambda x: self.refreshPackages())
        #self._searchentry.show()
        #searchtable.attach(self._searchentry, 1, 2, 0, 1)
        self._searchentry = qt.QLineEdit(self._searchbar)
        qt.QObject.connect(self._searchentry, qt.SIGNAL("returnPressed()"), self.refreshPackages)
        self._searchentry.show()

        #button = gtk.Button()
        #button.set_relief(gtk.RELIEF_NONE)
        #button.connect("clicked", lambda x: self.refreshPackages())
        #button.show()
        #searchtable.attach(button, 2, 3, 0, 1, 0, 0)
        #image = gtk.Image()
        #image.set_from_stock("gtk-find", gtk.ICON_SIZE_BUTTON)
        #image.show()
        #button.add(image)
        button = qt.QPushButton(self._searchbar)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.refreshPackages)
        pixmap = getPixmap("crystal-search")
        button.setIconSet(qt.QIconSet(pixmap))
        button.show()

        #align = gtk.Alignment()
        #align.set(1, 0, 0, 0)
        #align.set_padding(0, 0, 10, 0)
        #align.show()
        #searchtable.attach(align, 3, 4, 0, 1, gtk.FILL, gtk.FILL)
        #button = gtk.Button()
        #button.set_size_request(20, 20)
        #button.set_relief(gtk.RELIEF_NONE)
        #button.connect("clicked", lambda x: self.toggleSearch())
        #button.show()
        #align.add(button)
        #image = gtk.Image()
        #image.set_from_stock("gtk-close", gtk.ICON_SIZE_MENU)
        #image.show()
        #button.add(image)

        #hbox = gtk.HBox()
        #hbox.set_spacing(10)
        #hbox.show()
        #searchtable.attach(hbox, 1, 2, 1, 2)

        buttongroup = qt.QButtonGroup(self._searchbar)
        buttongroup.hide()
        
        #self._searchname = gtk.RadioButton(None, _("Automatic"))
        #self._searchname.set_active(True)
        #self._searchname.connect("clicked", lambda x: self.refreshPackages())
        #self._searchname.show()
        #hbox.pack_start(self._searchname, False)
        #self._searchdesc = gtk.RadioButton(self._searchname, _("Description"))
        #self._searchdesc.connect("clicked", lambda x: self.refreshPackages())
        #self._searchdesc.show()
        #hbox.pack_start(self._searchdesc, False)
        self._searchname = qt.QRadioButton(_("Automatic"), self._searchbar)
        self._searchname.setChecked(True)
        qt.QObject.connect(self._searchname, qt.SIGNAL("clicked()"), self.refreshPackages)
        buttongroup.insert(self._searchname)
        self._searchname.show()
        self._searchdesc = qt.QRadioButton(_("Description"), self._searchbar)
        self._searchdesc.setChecked(False)
        qt.QObject.connect(self._searchdesc, qt.SIGNAL("clicked()"), self.refreshPackages)
        self._searchdesc.show()
        buttongroup.insert(self._searchdesc)

        # Packages and information

        self._central = qt.QWidget(self._window)
        self._window.setCentralWidget(self._central)
        self._vbox = qt.QVBoxLayout(self._central)
        
        #self._vpaned = gtk.VPaned()
        #self._vpaned.show()
        #self._topvbox.pack_start(self._vpaned)

        #self._pv = GtkPackageView()
        #self._pv.show()
        #self._vpaned.pack1(self._pv, True)
        self._pv = QtPackageView(self._central)
        self._pv.show()
        self._vbox.addWidget(self._pv)

        #self._pi = GtkPackageInfo()
        #self._pi.show()
        #self._pv.connect("package_selected",
        #                 lambda x, y: self._pi.setPackage(y))
        #self._pv.connect("package_activated",
        #                 lambda x, y: self.actOnPackages(y))
        #self._pv.connect("package_popup", self.packagePopup)
        #self._vpaned.pack2(self._pi, False)
        self._pi = QtPackageInfo(self._central)
        self._pi.setMinimumSize(640,220) # HACK
        self._pi.show()
        qt.QObject.connect(self._pv, qt.PYSIGNAL("packageSelected"), self._pi.setPackage)
        qt.QObject.connect(self._pv, qt.PYSIGNAL("packageActivated"), self.actOnPackages)
        qt.QObject.connect(self._pv, qt.PYSIGNAL("packagePopup"), self.packagePopup)
        self._vbox.addWidget(self._pi)

        self._status = self._window.statusBar()
        self._status.show()

    def showStatus(self, msg):
        #self._status.pop(0)
        #self._status.push(0, msg)
        #while gtk.events_pending():
        #    gtk.main_iteration()
        self._status.message(msg)

    def hideStatus(self):
        #self._status.pop(0)
        #while gtk.events_pending():
        #    gtk.main_iteration()
        self._status.clear()

    def run(self, command=None, argv=None):
        self.setCatchExceptions(True)
        self.loadState()
        self._window.setIcon(getPixmap("smart"))
        self._window.show()
        self._ctrl.reloadChannels()
        self._changeset = ChangeSet(self._ctrl.getCache())
        self._pi.setChangeSet(self._changeset)
        self._progress.hide()
        self.refreshPackages()
        #gtk.main()
        app.exec_loop()
        self.saveState()
        self.setCatchExceptions(False)

    # Non-standard interface methods:

    def saveState(self):
        #sysconf.set("gtk-size", self._window.get_size())
        #sysconf.set("gtk-position", self._window.get_position())
        #sysconf.set("gtk-vpaned-position", self._vpaned.get_position())
        pass

    def loadState(self):
        #var = sysconf.get("gtk-size")
        #if var is not None:
        #    self._window.set_size_request(*var)
        #var = sysconf.get("gtk-position")
        #if var is not None:
        #    self._window.move(*var)
        #var = sysconf.get("gtk-vpaned-position")
        #if var is not None:
        #    self._vpaned.set_position(var)
        pass

    def getChangeSet(self):
        return self._changeset

    def updateChannels(self, selected=False, channels=None):
        #if selected:
        #    aliases = GtkChannelSelector().show()
        #    channels = [channel for channel in self._ctrl.getChannels()
        #                if channel.getAlias() in aliases]
        #    if not channels:
        #        return
        state = self._changeset.getPersistentState()
        self._ctrl.reloadChannels(channels, caching=NEVER)
        self._changeset.setPersistentState(state)
        self.refreshPackages()

    def rebuildCache(self):
        state = self._changeset.getPersistentState()
        self._ctrl.reloadChannels()
        self._changeset.setPersistentState(state)
        self.refreshPackages()

    def applyChanges(self, confirm=True):
        transaction = Transaction(self._ctrl.getCache(),
                                  changeset=self._changeset)
        if self._ctrl.commitTransaction(transaction, confirm=confirm):
            del self._undo[:]
            del self._redo[:]
            self._actions["redo"].setEnabled(False)
            self._actions["undo"].setEnabled(False)
            self._changeset.clear()
            self._ctrl.reloadChannels()
            self.refreshPackages()
            self.changedMarks()
        self._progress.hide()

    def clearChanges(self):
        self.saveUndo()
        self._changeset.clear()
        self.changedMarks()

    def showChanges(self):
        return self._changes.showChangeSet(self._changeset)

    def showLog(self):
        return self._log.show()

    def expandPackages(self):
        self._pv.expandAll()

    def collapsePackages(self):
        self._pv.collapseAll()

    def toggleFilter(self, filter):
        if filter in self._filters:
            del self._filters[filter]
        else:
            self._filters[filter] = True
        self.refreshPackages()

    def upgradeAll(self):
        transaction = Transaction(self._ctrl.getCache())
        transaction.setState(self._changeset)
        for pkg in self._ctrl.getCache().getPackages():
            if pkg.installed:
                transaction.enqueue(pkg, UPGRADE)
        transaction.setPolicy(PolicyUpgrade)
        transaction.run()
        changeset = transaction.getChangeSet()
        if changeset != self._changeset:
            if self.confirmChange(self._changeset, changeset):
                self.saveUndo()
                emptychangeset = not self._changeset
                self._changeset.setState(changeset)
                self.changedMarks()
                if self.askYesNo(_("Apply marked changes now?"), True):
                    self.applyChanges(confirm=not emptychangeset)
        else:
            self.showStatus(_("No interesting upgrades available!"))

    def actOnPackages(self, pkgs, op=None):
        cache = self._ctrl.getCache()
        transaction = Transaction(cache, policy=PolicyInstall)
        transaction.setState(self._changeset)
        changeset = transaction.getChangeSet()
        if op is None:
            if not [pkg for pkg in pkgs if pkg not in changeset]:
                op = KEEP
            else:
                for pkg in pkgs:
                    if not pkg.installed:
                        op = INSTALL
                        break
                else:
                    op = REMOVE
        if op is REMOVE:
            transaction.setPolicy(PolicyRemove)
        policy = transaction.getPolicy()
        for pkg in pkgs:
            if op is KEEP:
                transaction.enqueue(pkg, op)
            elif op in (REMOVE, REINSTALL, FIX):
                if pkg.installed:
                    transaction.enqueue(pkg, op)
                    if op is REMOVE:
                        for _pkg in cache.getPackages(pkg.name):
                            if not _pkg.installed:
                                policy.setLocked(_pkg, True)
            elif op is INSTALL:
                if not pkg.installed:
                    transaction.enqueue(pkg, op)
        transaction.run()
        if op is FIX:
            expected = 0
        else:
            expected = 1
        if self.confirmChange(self._changeset, changeset, expected):
            self.saveUndo()
            self._changeset.setState(changeset)
            self.changedMarks()

    def packagePopup(self, packageview, pkgs, pnt):
        
        menu = qt.QPopupMenu(packageview)
        menu.move(pnt)
        
        hasinstalled = bool([pkg for pkg in pkgs if pkg.installed
                             and self._changeset.get(pkg) is not REMOVE])
        hasnoninstalled = bool([pkg for pkg in pkgs if not pkg.installed
                                and self._changeset.get(pkg) is not INSTALL])

        class PackagesAction(object):
        
            def __init__(self, pkgs):
                self._pkgs = pkgs
                self._callback = {}
                self._userdata = {}
            
            def connect(self, item, callback, userdata):
                self._callback[item] = callback
                self._userdata[item] = userdata
            
            def slot(self, index):
                self._callback[index](self._pkgs, self._userdata[index])

        action = PackagesAction(pkgs)

        #image = gtk.Image()
        #image.set_from_pixbuf(getPixbuf("package-install"))
        #item = gtk.ImageMenuItem(_("Install"))
        #item.set_image(image)
        #item.connect("activate", lambda x: self.actOnPackages(pkgs, INSTALL))
        #if not hasnoninstalled:
        #    item.set_sensitive(False)
        #menu.append(item)
        iconset = qt.QIconSet(getPixmap("package-install"))
        item = menu.insertItem(iconset, _("Install"), action.slot)
        action.connect(item, self.actOnPackages, INSTALL)
        if not hasnoninstalled:
            menu.setItemEnabled(item, False)

        #image = gtk.Image()
        #image.set_from_pixbuf(getPixbuf("package-reinstall"))
        #item = gtk.ImageMenuItem(_("Reinstall"))
        #item.set_image(image)
        #item.connect("activate", lambda x: self.actOnPackages(pkgs, REINSTALL))
        #if not hasinstalled:
        #    item.set_sensitive(False)
        #menu.append(item)
        iconset = qt.QIconSet(getPixmap("package-reinstall"))
        item = menu.insertItem(iconset, _("Reinstall"), action.slot)
        action.connect(item, self.actOnPackages, REINSTALL)
        if not hasinstalled:
            menu.setItemEnabled(item, False)

        #image = gtk.Image()
        #image.set_from_pixbuf(getPixbuf("package-remove"))
        #item = gtk.ImageMenuItem(_("Remove"))
        #item.set_image(image)
        #item.connect("activate", lambda x: self.actOnPackages(pkgs, REMOVE))
        #if not hasinstalled:
        #    item.set_sensitive(False)
        #menu.append(item)
        iconset = qt.QIconSet(getPixmap("package-remove"))
        item = menu.insertItem(iconset, _("Remove"), action.slot)
        action.connect(item, self.actOnPackages, REMOVE)
        if not hasinstalled:
            menu.setItemEnabled(item, False)

        #image = gtk.Image()
        #if not hasinstalled:
        #    image.set_from_pixbuf(getPixbuf("package-available"))
        #else:
        #    image.set_from_pixbuf(getPixbuf("package-installed"))
        #item = gtk.ImageMenuItem(_("Keep"))
        #item.set_image(image)
        #item.connect("activate", lambda x: self.actOnPackages(pkgs, KEEP))
        #if not [pkg for pkg in pkgs if pkg in self._changeset]:
        #    item.set_sensitive(False)
        #menu.append(item)
        if not hasinstalled:
            iconset = qt.QIconSet(getPixmap("package-available"))
        else:
            iconset = qt.QIconSet(getPixmap("package-installed"))
        item = menu.insertItem(iconset, _("Keep"), action.slot)
        action.connect(item, self.actOnPackages, KEEP)
        if not [pkg for pkg in pkgs if pkg in self._changeset]:
            menu.setItemEnabled(item, False)

        #image = gtk.Image()
        #image.set_from_pixbuf(getPixbuf("package-broken"))
        #item = gtk.ImageMenuItem(_("Fix problems"))
        #item.set_image(image)
        #item.connect("activate", lambda x: self.actOnPackages(pkgs, FIX))
        #if not hasinstalled:
        #    item.set_sensitive(False)
        #menu.append(item)
        iconset = qt.QIconSet(getPixmap("package-broken"))
        item = menu.insertItem(iconset, _("Fix problems"))
        action.connect(item, self.actOnPackages, FIX)
        if not hasinstalled:
            menu.setItemEnabled(item, False)

        inconsistent = False
        thislocked = None
        alllocked = None
        names = pkgconf.getFlagTargets("lock")
        if [pkg for pkg in pkgs if pkg in self._changeset]:
            inconsistent = True
        else:
            for pkg in pkgs:
                if (names and pkg.name in names and 
                    ("=", pkg.version) in names[pkg.name]):
                    newthislocked = True
                    newalllocked = len(names[pkg.name]) > 1
                else:
                    newthislocked = False
                    newalllocked = pkgconf.testFlag("lock", pkg)
                if (thislocked is not None and thislocked != newthislocked or
                    alllocked is not None and alllocked != newalllocked):
                    inconsistent = True
                    break
                thislocked = newthislocked
                alllocked = newalllocked

        #image = gtk.Image()
        #if thislocked:
        #    item = gtk.ImageMenuItem(_("Unlock this version"))
        #    if not hasnoninstalled:
        #        image.set_from_pixbuf(getPixbuf("package-installed"))
        #    else:
        #        image.set_from_pixbuf(getPixbuf("package-available"))
        #    def unlock_this(x):
        #        for pkg in pkgs:
        #            pkgconf.clearFlag("lock", pkg.name, "=", pkg.version)
        #        #self._pv.queue_draw()
        #        #self._pi.setPackage(pkgs[0])
        #    item.connect("activate", unlock_this)
        #else:
        #    item = gtk.ImageMenuItem(_("Lock this version"))
        #    if not hasnoninstalled:
        #        image.set_from_pixbuf(getPixbuf("package-installed-locked"))
        #    else:
        #        image.set_from_pixbuf(getPixbuf("package-available-locked"))
        #    def lock_this(x):
        #        for pkg in pkgs:
        #            pkgconf.setFlag("lock", pkg.name, "=", pkg.version)
        #        #self._pv.queue_draw()
        #        #self._pi.setPackage(pkgs[0])
        #    item.connect("activate", lock_this)
        #item.set_image(image)
        #if inconsistent:
        #    item.set_sensitive(False)
        #menu.append(item)
        if thislocked:
            if not hasnoninstalled:
                iconset = qt.QIconSet(getPixmap("package-installed"))
            else:
                iconset = qt.QIconSet(getPixmap("package-available"))
            item = menu.insertItem(iconset, _("Unlock this version"))
        else:
            if not hasnoninstalled:
                iconset = qt.QIconSet(getPixmap("package-installed-locked"))
            else:
                iconset = qt.QIconSet(getPixmap("package-available-locked"))
            item = menu.insertItem(iconset, _("Lock this version"))
        if inconsistent or True:
            menu.setItemEnabled(item, False)

        #image = gtk.Image()
        #if alllocked:
        #    item = gtk.ImageMenuItem(_("Unlock all versions"))
        #    if not hasnoninstalled:
        #        image.set_from_pixbuf(getPixbuf("package-installed"))
        #    else:
        #        image.set_from_pixbuf(getPixbuf("package-available"))
        #    def unlock_all(x):
        #        for pkg in pkgs:
        #            pkgconf.clearFlag("lock", pkg.name)
        #        #self._pv.queue_draw()
        #        #self._pi.setPackage(pkgs[0])
        #    item.connect("activate", unlock_all)
        #else:
        #    item = gtk.ImageMenuItem(_("Lock all versions"))
        #    if not hasnoninstalled:
        #        image.set_from_pixbuf(getPixbuf("package-installed-locked"))
        #    else:
        #       image.set_from_pixbuf(getPixbuf("package-available-locked"))
        #    def lock_all(x):
        #        for pkg in pkgs:
        #           pkgconf.setFlag("lock", pkg.name)
        #        #self._pv.queue_draw()
        #        #self._pi.setPackage(pkgs[0])
        #    item.connect("activate", lock_all)
        #item.set_image(image)
        #if inconsistent:
        #    item.set_sensitive(False)
        #menu.append(item)
        if alllocked:
            if not hasnoninstalled:
                iconset = qt.QIconSet(getPixmap("package-installed"))
            else:
                iconset = qt.QIconSet(getPixmap("package-available"))
            item = menu.insertItem(iconset, _("Unlock all versions"))
        else:
            if not hasnoninstalled:
                iconset = qt.QIconSet(getPixmap("package-installed-locked"))
            else:
                iconset = qt.QIconSet(getPixmap("package-available-locked"))
            item = menu.insertItem(iconset, _("Lock all versions"))
        if inconsistent or True:
            menu.setItemEnabled(item, False)

        #item = gtk.MenuItem(_("Priority"))
        #def priority(x):
        #    GtkSinglePriority(self._window).show(pkgs[0])
        #    self._pi.setPackage(pkgs[0])
        #item.connect("activate", priority)
        #if len(pkgs) != 1:
        #    item.set_sensitive(False)
        #menu.append(item)
        item = menu.insertItem(_("Priority"))
        if len(pkgs) != 1:
            menu.setItemEnabled(item, False)

        menu.show()
        #menu.popup(None, None, None, event.button, event.time)
        menu.exec_loop(packageview.mapToGlobal(pnt))

    def checkPackages(self, all=False, uninstalled=False):
        installed = not uninstalled
        available = all or uninstalled
        self.info(_("Checking relations..."))
        if checkPackagesSimple(self._ctrl.getCache(), report=True,
                               installed=installed, available=available):
            self.info(_("All checked packages have correct relations."))

    def fixAllProblems(self):
        self.actOnPackages([pkg for pkg in self._ctrl.getCache().getPackages()
                            if pkg.installed], FIX)

    def undo(self):
        if self._undo:
            state = self._undo.pop(0)
            if not self._undo:
                self._actions["undo"].setEnabled(False)
            self._redo.insert(0, self._changeset.getPersistentState())
            self._actions["redo"].setEnabled(True)
            self._changeset.setPersistentState(state)
            self.changedMarks()

    def redo(self):
        if self._redo:
            state = self._redo.pop(0)
            if not self._redo:
                self._actions["redo"].setEnabled(False)
            self._undo.insert(0, self._changeset.getPersistentState())
            self._actions["undo"].setEnabled(True)
            self._changeset.setPersistentState(state)
            self.changedMarks()

    def saveUndo(self):
        self._undo.insert(0, self._changeset.getPersistentState())
        del self._redo[:]
        del self._undo[20:]
        self._actions["undo"].setEnabled(True)
        self._actions["redo"].setEnabled(False)

    def setTreeStyle(self, mode):
        if mode != sysconf.get("package-tree"):
            sysconf.set("package-tree", mode)
            self.refreshPackages()

    def editChannels(self):
        #if GtkChannels(self._window).show():
        #    self.rebuildCache()
        pass

    def editMirrors(self):
        #GtkMirrors(self._window).show()
        pass

    def editFlags(self):
        #GtkFlags(self._window).show()
        pass

    def editPriorities(self):
        #GtkPriorities(self._window).show()
        pass

    def setBusy(self, flag):
        if flag:
            #self._window.window.set_cursor(self._watch)
            #while gtk.events_pending():
            #    gtk.main_iteration()
            while qt.QApplication.eventLoop().hasPendingEvents():
                qt.QApplication.eventLoop().processEvents(qt.QEventLoop.AllEvents)
            pass
        else:
            #self._window.window.set_cursor(None)
            pass

    def changedMarks(self):
        if "hide-unmarked" in self._filters:
            self.refreshPackages()
        else:
            #self._pv.queue_draw()
            pass
        self._actions["exec-changes"].setEnabled(bool(self._changeset))
        self._actions["clear-changes"].setEnabled(bool(self._changeset))
        

    def toggleSearch(self):
        visible = not self._searchentry.isVisible()
        if visible:
            self._searchbar.show()
        else:
            self._searchbar.hide()
        self.refreshPackages()
        if visible:
            self._searchentry.setFocus()
            pass

    def refreshPackages(self):
        if not self._ctrl:
            return

        self.setBusy(True)

        tree = sysconf.get("package-tree", "groups")
        ctrl = self._ctrl
        changeset = self._changeset

        if self._searchbar.isVisible() and \
            self._searchentry.text(): # temporary

            searcher = Searcher()
            dosearch = False
            if self._searchdesc.isChecked():
                text = self._searchentry.text()
                if text:
                    text = str(text).strip()
                    dosearch = True
                    searcher.addDescription(text)
                    searcher.addSummary(text)
            else:
                try:
                    text = self._searchentry.text()
                    tokens = shlex.split(str(text))
                except ValueError:
                    pass
                else:
                    if tokens:
                        dosearch = True
                        for tok in tokens:
                            if searcher.hasAutoMeaning(tok):
                                searcher.addAuto(tok)
                            else:
                                searcher.addNameVersion("*%s*" % tok)

            packages = []
            if dosearch:
                self._ctrl.getCache().search(searcher)
                for ratio, obj in searcher.getResults():
                    if isinstance(obj, Package):
                        packages.append(obj)
                    else:
                        packages.extend(obj.packages)
        else:
            packages = ctrl.getCache().getPackages()

        filters = self._filters
        if filters:
            if "hide-non-upgrades" in filters:
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
            if "hide-old" in filters:
                packages = pkgconf.filterByFlag("new", packages)

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
                    channel = loader.getChannel()
                    group = channel.getName() or channel.getAlias()
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
                    channel = loader.getChannel()
                    group = channel.getName() or channel.getAlias()
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

        self.setBusy(False)

    def showAbout(self):
        license = """
            This program is free software; you can redistribute it and/or modify
            it under the terms of the GNU General Public License as published by
            the Free Software Foundation; either version 2 of the License, or
            (at your option) any later version.

            This program is distributed in the hope that it will be useful,
            but WITHOUT ANY WARRANTY; without even the implied warranty of
            MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
            GNU General Public License for more details.

            You should have received a copy of the GNU General Public License
            along with this program; if not, write to the Free Software
            Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
            """
        credits=["""Gustavo Niemeyer - Original author and lead developer.""",
            """Conectiva Inc. - Original project funder up to August 2005.""",
            """Canonical Ltd. - Funding Smart development since September of 2005.""",
            """And many others - Check our website for the complete list.""",
            ]
        website = "http://labix.org/smart"    

        qt.QMessageBox.about(self._window, "About " + "Smart Package Manager",
            "<h2>Smart Package Manager " + VERSION + "</h2>" + \
            "<p>Copyright &copy; " + "2006 Canonical, 2004 Conectiva, Inc." + \
            "<p><small>" + license + "</small>" + \
            "<p><h3>Credits</h3>" + "<br>".join(credits) + \
            "<p><a href=\""+website+"\">"+website+"</a>")

# vim:ts=4:sw=4:et

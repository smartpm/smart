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
from smart.interfaces.qt4.channels import QtChannels, QtChannelSelector
from smart.interfaces.qt4.mirrors import QtMirrors
from smart.interfaces.qt4.flags import QtFlags
from smart.interfaces.qt4.priorities import QtPriorities, QtSinglePriority
from smart.interfaces.qt4.packageview import QtPackageView
from smart.interfaces.qt4.packageinfo import QtPackageInfo
from smart.interfaces.qt4.legend import QtLegend
from smart.interfaces.qt4.interface import QtInterface, app
from smart.interfaces.qt4 import getPixmap, centerWindow
from smart.const import NEVER, VERSION
from smart.searcher import Searcher
from smart.cache import Package
from smart import *
import shlex, re
import fnmatch
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

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
        "hide-unlocked",
        "hide-requested",
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
        "legend-window",
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
     _("Update channels"), "self.updateChannels()"),
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
    ("legend-window", None, _("_Icon Legend"), None,
     _("Show icon legend"), "self._legend.show()"),
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
        #act = QtGui.QAction(group, action[0])
        act = QtGui.QAction(group)
        #act.setText(action[0])
        #act.setMenuText(action[2].replace("_","&"))
        act.setText(action[2].replace("_","&"))
        if len(action) > 4:
            act.setToolTip(action[4])
        if len(action) > 5 and type(action[5]) is not str:
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()") , action[5])
        if action[0] == "find": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.toggleSearch)
        if action[0] == "update-selected-channels": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.selectedChannels)
        if action[0] == "update-channels": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.allChannels)
        if action[0] == "rebuild-cache": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.rebuildCache)
        if action[0] == "upgrade-all": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.upgradeAll)
        if action[0] == "exec-changes": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.applyChanges)
        if action[0] == "clear-changes": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.clearChanges)
        if action[0] == "expand-all": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.expandPackages)
        if action[0] == "collapse-all": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.collapsePackages)
        if action[0] == "edit-channels": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.editChannels)
        if action[0] == "edit-mirrors": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.editMirrors)
        if action[0] == "edit-flags": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.editFlags)
        if action[0] == "edit-priorities": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.editPriorities)
        if action[0] == "summary-window": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.showChanges)
        if action[0] == "log-window": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.showLog)
        if action[0] == "legend-window": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.showLegend)
        if action[0] == "about": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), self.showAbout)
        if action[0] == "quit": #HACK
            self = globals["self"]
            QtCore.QObject.connect(act, QtCore.SIGNAL("activated()"), app, QtCore.SLOT("quit()"))
        group.addAction(act)
        #newactions[action[0]] = tuple(action)
        newactions[action[0]] = act
    return newactions

class QtInteractiveInterface(QtInterface):

    def __init__(self, ctrl, argv=None):
        QtInterface.__init__(self, ctrl, argv)

        self._changeset = None

        self._window = QtGui.QMainWindow()
        self._window.setWindowTitle("Smart Package Manager %s" % VERSION)
        centerWindow(self._window)
        self._window.setMinimumSize(640, 480)
        app.connect(app, QtCore.SIGNAL('lastWindowClosed()'), app, QtCore.SLOT('quit()'))

        self._undo = []
        self._redo = []

        globals = {"self": self, "QtGui": QtGui, "QtCore": QtCore}
        #group = QtGui.QActionGroup(self._window, "Actions")
        group = QtGui.QActionGroup(self._window)
        self._actions = compileActions(group, ACTIONS, globals)

        class ToggleAction(QtGui.QAction):
        
            def __init__(self, group, name, label):
                QtGui.QAction.__init__(self, name, group)
                #self.setToggleAction(True)
                self.setCheckable(True)
                self.setText(label.replace("&","&&"))
                self._name = name
            
            def connect(self, signal, callback, userdata):
                self._callback = callback
                self._userdata = userdata
                QtCore.QObject.connect(self, QtCore.SIGNAL(signal), self.slot)
            
            def slot(self):
                self._callback(self._userdata)
         
        self._filters = {}
        for name, label in [("hide-non-upgrades", _("Hide Non-upgrades")),
                            ("hide-installed", _("Hide Installed")),
                            ("hide-uninstalled", _("Hide Uninstalled")),
                            ("hide-unmarked", _("Hide Unmarked")),
                            ("hide-unlocked", _("Hide Unlocked")),
                            ("hide-requested", _("Hide Requested")),
                            ("hide-old", _("Hide Old"))]:
            act = ToggleAction(None, name, label)
            act.connect("activated()", self.toggleFilter, name)
            self._actions[name] = act

        treestyle = sysconf.get("package-tree")
        for name, label in [("groups", _("Groups")),
                            ("channels", _("Channels")),
                            ("channels-groups", _("Channels & Groups")),
                            ("none", _("None"))]:
            act = ToggleAction(group, "tree-style-"+name, label)
            if name == treestyle:
                act.setChecked(True)
            act.connect("activated()", self.setTreeStyle, name)
            self._actions["tree-style-"+name] = act

        self._menubar = self._window.menuBar()
        for MENU in MENUBAR:
             def insertmenu(menubar, menu):
                item = menu[0]
                action = self._actions[item]
                m = QtGui.QMenu(menubar)
                m.setTitle(action.text())
                menubar.addMenu(m)
                for item in menu[1]:
                    if isinstance(item, tuple):
                        insertmenu(m, item)
                    elif item:
                        action = self._actions[item]
                        #i = QtGui.QPopupMenu(m)
                        i = QtGui.QMenu(m)
                        #text = action.menuText()
                        i.setTitle(action.text())
                        #m.insertItem(text, i)
                        #action.addTo(m)
                        m.addAction(action)
                    else:
                        m.addSeparator()
             insertmenu(self._menubar, MENU)

        self._toolbar = QtGui.QToolBar(self._window)
        for TOOL in TOOLBAR:
            def inserttool(toolbar, tool):
                if tool:
                    action = self._actions[tool]
                    pixmap = getPixmap(TOOLBARICONS[tool])
                    action.setIcon(QtGui.QIcon(pixmap))
                    toolbar.addAction(action)
                else:
                    toolbar.addSeparator()
            inserttool(self._toolbar, TOOL)
            self._window.addToolBar( self._toolbar)

        #self._window.add_accel_group(self._ui.get_accel_group())

        self._actions["exec-changes"].setShortcut(QtGui.QKeySequence("Ctrl+C"))
        self._actions["find"].setShortcut(QtGui.QKeySequence("Ctrl+F"))
        self._actions["expand-all"].setShortcut(QtGui.QKeySequence("Ctrl+O"))
        self._actions["collapse-all"].setShortcut(QtGui.QKeySequence("Ctrl+W"))
        self._actions["summary-window"].setShortcut(QtGui.QKeySequence("Ctrl+S"))

        self._actions["exec-changes"].setEnabled(False)
        self._actions["clear-changes"].setEnabled(False)
        self._actions["undo"].setEnabled(False)
        self._actions["redo"].setEnabled(False)

        # Search bar

        self._searchbar = QtGui.QToolBar(self._window)
        self._searchbar.hide()
        self._window.addToolBar(self._searchbar)
       
        label = QtGui.QLabel(_("Search:"), self._searchbar)
        label.show()
        self._searchbar.addWidget(label)

        self._searchentry = QtGui.QLineEdit(self._searchbar)
        QtCore.QObject.connect(self._searchentry, QtCore.SIGNAL("returnPressed()"), self.refreshPackages)
        self._searchentry.show()
        self._searchbar.addWidget(self._searchentry)

        button = QtGui.QPushButton(self._searchbar)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.refreshPackages)
        pixmap = getPixmap("crystal-search")
        button.setIcon(QtGui.QIcon(pixmap))
        button.show()
        self._searchbar.addWidget(button)

        buttongroup = QtGui.QButtonGroup(self._searchbar)
        #buttongroup.hide()
        
        self._searchname = QtGui.QRadioButton(_("Automatic"), self._searchbar)
        self._searchname.setChecked(True)
        QtCore.QObject.connect(self._searchname, QtCore.SIGNAL("clicked()"), self.refreshPackages)
        buttongroup.addButton(self._searchname)
        self._searchbar.addWidget(self._searchname)
        self._searchname.show()
        self._searchdesc = QtGui.QRadioButton(_("Description"), self._searchbar)
        self._searchdesc.setChecked(False)
        QtCore.QObject.connect(self._searchdesc, QtCore.SIGNAL("clicked()"), self.refreshPackages)
        self._searchdesc.show()
        buttongroup.addButton(self._searchdesc)
        self._searchbar.addWidget(self._searchdesc)

        # Packages and information

        self._splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self._window)
        self._window.setCentralWidget(self._splitter)
        
        self._pv = QtPackageView(self._splitter)
        self._pv.show()

        self._pi = QtPackageInfo(self._splitter)
        self._pi.show()
        QtCore.QObject.connect(self._pv, QtCore.SIGNAL("packageSelected"), self._pi.setPackage)
        QtCore.QObject.connect(self._pv, QtCore.SIGNAL("packageActivated"), self.actOnPackages)
        QtCore.QObject.connect(self._pv, QtCore.SIGNAL("packagePopup"), self.packagePopup)

        self._status = self._window.statusBar()
        self._status.show()

        self._legend = QtLegend(self._window)

    def showStatus(self, msg):
        self._status.showMessage(msg)

    def hideStatus(self):
        self._status.clearMessage()

    def run(self, command=None, argv=None):
        self.setCatchExceptions(True)
        self.loadState()
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.show()
        self._ctrl.reloadChannels()
        self._changeset = ChangeSet(self._ctrl.getCache())
        self._pi.setChangeSet(self._changeset)
        self._progress.hide()
        self.refreshPackages()
        app.exec_()
        self.saveState()
        self.setCatchExceptions(False)

    # Non-standard interface methods:

    def saveState(self):
        # Note: QtCore.QSize and QtCore.QPoint are not pickleable, unfortunately
        sysconf.set("qt-size", (self._window.width(),self._window.height()))
        sysconf.set("qt-position", (self._window.x(),self._window.y()))
        sysconf.set("qt-splitter-sizes", self._splitter.sizes())

    def loadState(self):
        var = sysconf.get("qt-size")
        if var is not None:
            self._window.resize(*var)
        var = sysconf.get("qt-position")
        if var is not None:
            self._window.move(*var)
        var = sysconf.get("qt-splitter-sizes")
        if var is not None:
            self._splitter.setSizes(var)

    def getChangeSet(self):
        return self._changeset

    def selectedChannels(self):
        self.updateChannels(selected=True)

    def allChannels(self):
        self.updateChannels(selected=False)

    def updateChannels(self, selected=False, channels=None):
        if selected:
            aliases = QtChannelSelector().show()
            channels = [channel for channel in self._ctrl.getChannels()
                        if channel.getAlias() in aliases]
            if not channels:
                return
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

    def showLegend(self):
        return self._legend.show()

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
            self.changedMarks(pkgs)

    def lockPackages(self, pkgs, lock):
        if not lock:
             for pkg in pkgs:
                  pkgconf.clearFlag("lock", pkg.name, "=", pkg.version)
             self._pv.update()
             self._pi.setPackage(pkgs[0])
        else:
             for pkg in pkgs:
                  pkgconf.setFlag("lock", pkg.name, "=", pkg.version)
             self._pv.update()
             self._pi.setPackage(pkgs[0])

    def lockAllPackages(self, pkgs, lock):
        if not lock:
             for pkg in pkgs:
                  pkgconf.clearFlag("lock", pkg.name)
             self._pv.update()
             self._pi.setPackage(pkgs[0])
        else:
             for pkg in pkgs:
                  pkgconf.setFlag("lock", pkg.name)
             self._pv.update()
             self._pi.setPackage(pkgs[0])

    def priorityPackages(self, pkgs, none):
        QtSinglePriority(self._window).show(pkgs[0])
        self._pi.setPackage(pkgs[0])

    def packagePopup(self, packageview, pkgs, pnt):
        
        menu = QtGui.QMenu(packageview)
        menu.move(pnt)
        
        hasinstalled = bool([pkg for pkg in pkgs if pkg.installed
                             and self._changeset.get(pkg) is not REMOVE])
        hasnoninstalled = bool([pkg for pkg in pkgs if not pkg.installed
                                and self._changeset.get(pkg) is not INSTALL])

        class PackagesAction(object):
        
            def __init__(self, pkgs):
                self._pkgs = pkgs
                self._callback = None
                self._userdata = None
            
            def connect(self, item, callback, userdata=None):
                self._callback = callback
                self._userdata = userdata
            
            def slot(self):
                self._callback(self._pkgs, self._userdata)

        installaction = PackagesAction(pkgs)

        iconset = QtGui.QIcon(getPixmap("package-install"))
        item = menu.addAction(iconset, _("Install"), installaction.slot)
        installaction.connect(item, self.actOnPackages, INSTALL)
        if not hasnoninstalled:
            item.setEnabled(False)

        reinstallaction = PackagesAction(pkgs)

        iconset = QtGui.QIcon(getPixmap("package-reinstall"))
        item = menu.addAction(iconset, _("Reinstall"), reinstallaction.slot)
        reinstallaction.connect(item, self.actOnPackages, REINSTALL)
        if not hasinstalled:
            item.setEnabled(False)

        removeaction = PackagesAction(pkgs)

        iconset = QtGui.QIcon(getPixmap("package-remove"))
        item = menu.addAction(iconset, _("Remove"), removeaction.slot)
        removeaction.connect(item, self.actOnPackages, REMOVE)
        if not hasinstalled:
            item.setEnabled(False)

        keepaction = PackagesAction(pkgs)

        if not hasinstalled:
            iconset = QtGui.QIcon(getPixmap("package-available"))
        else:
            iconset = QtGui.QIcon(getPixmap("package-installed"))
        item = menu.addAction(iconset, _("Keep"), keepaction.slot)
        keepaction.connect(item, self.actOnPackages, KEEP)
        if not [pkg for pkg in pkgs if pkg in self._changeset]:
            item.setEnabled(False)

        fixaction = PackagesAction(pkgs)

        iconset = QtGui.QIcon(getPixmap("package-broken"))
        item = menu.addAction(iconset, _("Fix problems"), fixaction.slot)
        fixaction.connect(item, self.actOnPackages, FIX)
        if not hasinstalled:
            item.setEnabled(False)

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

        lockaction = PackagesAction(pkgs)

        if thislocked:
            if not hasnoninstalled:
                iconset = QtGui.QIcon(getPixmap("package-installed"))
            else:
                iconset = QtGui.QIcon(getPixmap("package-available"))
            item = menu.addAction(iconset, _("Unlock this version"), lockaction.slot)
            lockaction.connect(item, self.lockPackages, False)
        else:
            if not hasnoninstalled:
                iconset = QtGui.QIcon(getPixmap("package-installed-locked"))
            else:
                iconset = QtGui.QIcon(getPixmap("package-available-locked"))
            item = menu.addAction(iconset, _("Lock this version"), lockaction.slot)
            lockaction.connect(item, self.lockPackages, True)
        if inconsistent:
            item.setEnabled(False)

        lockallaction = PackagesAction(pkgs)

        if alllocked:
            if not hasnoninstalled:
                iconset = QtGui.QIcon(getPixmap("package-installed"))
            else:
                iconset = QtGui.QIcon(getPixmap("package-available"))
            item = menu.addAction(iconset, _("Unlock all versions"), lockallaction.slot)
            lockallaction.connect(item, self.lockAllPackages, False)
        else:
            if not hasnoninstalled:
                iconset = QtGui.QIcon(getPixmap("package-installed-locked"))
            else:
                iconset = QtGui.QIcon(getPixmap("package-available-locked"))
            item = menu.addAction(iconset, _("Lock all versions"), lockallaction.slot)
            lockallaction.connect(item, self.lockAllPackages, True)
        if inconsistent:
            item.setEnabled(False)

        priorityaction = PackagesAction(pkgs)
        
        item = menu.addAction(_("Priority"), priorityaction.slot)
        priorityaction.connect(item, self.priorityPackages)
        if len(pkgs) != 1:
            item.setEnabled(False)

        menu.show()
        menu.exec_(packageview.mapToGlobal(pnt))

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
        if QtChannels(self._window).show():
            self.rebuildCache()

    def editMirrors(self):
        QtMirrors(self._window).show()

    def editFlags(self):
        QtFlags(self._window).show()

    def editPriorities(self):
        QtPriorities(self._window).show()

    def setBusy(self, flag):
        if flag:
            QtGui.QApplication.setOverrideCursor( QtGui.QCursor(QtCore.Qt.WaitCursor) )
            #while QtGui.QApplication.eventLoop().hasPendingEvents():
            #    QtGui.QApplication.eventLoop().processEvents(QtGui.QEventLoop.AllEvents)
        else:
            QtGui.QApplication.restoreOverrideCursor()

    def changedMarks(self, pkgs=[]):
        if "hide-unmarked" in self._filters:
            self.refreshPackages()
        else:
            self._pv.updatePackages(pkgs, self._changeset)
            self._pv.update()
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
            if "hide-unlocked" in filters:
                packages = pkgconf.filterByFlag("lock", packages)
            if "hide-requested" in filters:
                packages = pkgconf.filterByFlag("auto", packages)
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
        copyright = "2010 Smart Team, 2006 Canonical Ltd., 2004 Conectiva, Inc."
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
           u"""Anders F Bj\u00f6rklund - Current maintainer and developer.""",
            """Conectiva Inc. - Original project funder up to August 2005.""",
            """Canonical Ltd. - Funded Smart up to November of 2009.""",
            """Unity Linux - Smart development and deployment support.""",
            """And many others - Check our website for the complete list.""",
            ]
        website = "http://smartpm.org/"

        QtGui.QMessageBox.about(self._window, "About " + "Smart Package Manager",
            "<h2>" + "Smart Package Manager" + " " + VERSION + "</h2>" + \
            "<p>Copyright &copy; " + copyright + \
            "<p><small>" + license + "</small>" + \
            "<p><h3>Credits</h3>" + "<br>".join(credits) + \
            "<p><a href=\""+website+"\">"+website+"</a>")

# vim:ts=4:sw=4:et

#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
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
from smart.interfaces.gtk.channels import GtkChannels, GtkChannelSelector
from smart.interfaces.gtk.mirrors import GtkMirrors
from smart.interfaces.gtk.flags import GtkFlags
from smart.interfaces.gtk.priorities import GtkPriorities, GtkSinglePriority
from smart.interfaces.gtk.packageview import GtkPackageView
from smart.interfaces.gtk.packageinfo import GtkPackageInfo
from smart.interfaces.gtk.legend import GtkLegend
from smart.interfaces.gtk.interface import GtkInterface
from smart.interfaces.gtk import getPixbuf
from smart.const import NEVER, VERSION
from smart.searcher import Searcher
from smart.cache import Package
from smart import *
import shlex, re
import fnmatch
import gobject, gtk
try:
    import sexy
except ImportError:
    sexy = None

UI = """
<ui>
<menubar>
    <menu action="file">
        <menuitem action="update-selected-channels"/>
        <menuitem action="update-channels"/>
        <separator/>
        <menuitem action="rebuild-cache"/>
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
        <menuitem action="fix-all-problems"/>
        <menuitem action="remove-auto"/>
        <separator/>
        <menuitem action="check-installed-packages"/>
        <menuitem action="check-uninstalled-packages"/>
        <menuitem action="check-all-packages"/>
        <separator/>
        <menuitem action="find"/>
        <separator/>
        <menuitem action="edit-channels"/>
        <menuitem action="edit-mirrors"/>
        <menuitem action="edit-flags"/>
        <menuitem action="edit-priorities"/>
    </menu>
    <menu action="view">
        <menuitem action="hide-non-upgrades"/>
        <menuitem action="hide-non-newest"/>
        <menuitem action="hide-installed"/>
        <menuitem action="hide-uninstalled"/>
        <menuitem action="hide-unmarked"/>
        <menuitem action="hide-unlocked"/>
        <menuitem action="hide-requested"/>
        <menuitem action="hide-old"/>
        <separator/>
        <menuitem action="expand-all"/>
        <menuitem action="collapse-all"/>
        <separator/>
        <menu action="tree-style">
            <menuitem action="tree-style-groups"/>
            <menuitem action="tree-style-separate-groups"/>
            <menuitem action="tree-style-channels"/>
            <menuitem action="tree-style-channels-groups"/>
            <menuitem action="tree-style-none"/>
        </menu>
        <separator/>
        <menuitem action="summary-window"/>
        <menuitem action="log-window"/>
    </menu>
    <menu action="help">
        <menuitem action="legend-window"/>
        <menuitem action="about"/>
    </menu>   
</menubar>
<toolbar>
    <toolitem action="update-channels"/>
    <separator/>
    <toolitem action="exec-changes"/>
    <separator/>
    <toolitem action="undo"/>
    <toolitem action="redo"/>
    <toolitem action="clear-changes"/>
    <separator/>
    <toolitem action="upgrade-all"/>
    <separator/>
    <toolitem action="find"/>
</toolbar>
</ui>
"""

ACTIONS = [
    ("file", None, _("_File")),
    ("update-selected-channels", "gtk-refresh", _("Update _Selected Channels..."), None,
     _("Update given channels"), "self.updateSelected()"),
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
    ("remove-auto", None, _("Remove Automatic..."), None,
     _("Remove packages installed as dependencies"), "self.removeAuto()"),
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
     _("Expand all items in the tree"), "self.expandPackages()"),
    ("collapse-all", "gtk-close", _("_Collapse All"), None,
     _("Collapse all items in the tree"), "self.collapsePackages()"),
    ("summary-window", None, _("_Summary Window"), "<control>s",
     _("Show summary window"), "self.showChanges()"),
    ("log-window", None, _("_Log Window"), None,
     _("Show log window"), "self.showLog()"),

    ("help", None, _("_Help")),
    ("legend-window", None, _("_Icon Legend"), None,
     _("Show icon legend"), "self.showLegend()"),
    ("about", None, _("_About"), None,
     _("Show about window"), "self.showAbout()"),


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

    def __init__(self, ctrl):
        GtkInterface.__init__(self, ctrl)

        self._changeset = None

        self._window = gtk.Window()
        self._window.set_title("Smart Package Manager %s" % VERSION)
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=640, min_height=480)
        def delete(widget, event):
            gtk.main_quit()
            return True
        self._window.connect("delete-event", delete)

        self._log.set_transient_for(self._window)
        self._progress.set_transient_for(self._window)
        self._hassubprogress.set_transient_for(self._window)
        self._changes.set_transient_for(self._window)

        self._watch = gtk.gdk.Cursor(gtk.gdk.WATCH)

        self._undo = []
        self._redo = []

        self._topvbox = gtk.VBox()
        self._topvbox.show()
        self._window.add(self._topvbox)

        globals = {"self": self, "gtk": gtk}
        self._actions = gtk.ActionGroup("Actions")
        self._actions.add_actions(compileActions(ACTIONS, globals))

        self._filters = {}
        for name, label in [("hide-non-upgrades", _("Hide Non-upgrades")),
                            ("hide-non-newest", _("Hide Non-newest")),
                            ("hide-installed", _("Hide Installed")),
                            ("hide-uninstalled", _("Hide Uninstalled")),
                            ("hide-unmarked", _("Hide Unmarked")),
                            ("hide-unlocked", _("Hide Unlocked")),
                            ("hide-requested", _("Hide Requested")),
                            ("hide-old", _("Hide Old"))]:
            action = gtk.ToggleAction(name, label, "", "")
            action.connect("toggled", lambda x, y: self.toggleFilter(y), name)
            self._actions.add_action(action)

        treestyle = sysconf.get("package-tree")
        lastaction = None
        for name, label in [("groups", _("Groups")),
                            ("separate-groups", _("Separate Groups")),
                            ("channels", _("Channels")),
                            ("channels-groups", _("Channels & Groups")),
                            ("none", _("None"))]:
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

        self._toolbar = self._ui.get_widget("/toolbar")
        self._toolbar.set_style(gtk.TOOLBAR_ICONS)
        self._topvbox.pack_start(self._toolbar, False)
        if sysconf.getReadOnly():
           # Can't update channels in readonly mode.
           updatetoolitem = self._ui.get_widget("/toolbar/update-channels")
           updatetoolitem.set_property("sensitive", False)

        self._window.add_accel_group(self._ui.get_accel_group())

        self._execmenuitem = self._ui.get_action("/menubar/file/exec-changes")
        self._execmenuitem.set_property("sensitive", False)
        self._clearmenuitem = self._ui.get_action("/menubar/edit/clear-changes")
        self._clearmenuitem.set_property("sensitive", False)
        self._undomenuitem = self._ui.get_action("/menubar/edit/undo")
        self._undomenuitem.set_property("sensitive", False)
        self._redomenuitem = self._ui.get_action("/menubar/edit/redo")
        self._redomenuitem.set_property("sensitive", False)

        # Search bar

        if gtk.gtk_version >= (2, 16, 0) or sexy:
            self._searchbar = gtk.ToolItem()
            self._searchbar.set_expand(True)
            self._searchbar.set_homogeneous(False)
            self._searchbar.show()
            count = self._toolbar.get_n_items()
            find = self._toolbar.get_nth_item(count - 1)
            self._toolbar.remove(find)
            self._toolbar.insert(self._searchbar, -1)

            searchtable = gtk.Table(1, 1)
            searchtable.set_row_spacings(5)
            searchtable.set_col_spacings(5)
            searchtable.set_border_width(5)
            searchtable.show()
            self._searchbar.add(searchtable)

            if gtk.gtk_version >= (2, 16, 0):
                self._searchentry = gtk.Entry()
                self._searchentry.set_property("primary-icon-name", "gtk-find")
                self._searchentry.set_property("secondary-icon-name", "gtk-clear")
                def press(entry, icon_pos, event):
                    if int(icon_pos) == 0: # "primary"
                        self._searchmenu.popup(None, None, None, event.button, event.time)
                    elif int(icon_pos) == 1: # "secondary"
                        self._searchentry.set_text("")
                        self.refreshPackages()
                self._searchentry.connect("icon-press", press)
            elif sexy:
                self._searchentry = sexy.IconEntry()
                image = gtk.Image()
                image.set_from_stock("gtk-find", gtk.ICON_SIZE_BUTTON)
                self._searchentry.set_icon(sexy.ICON_ENTRY_PRIMARY, image)
                image = gtk.Image()
                image.set_from_stock("gtk-clear", gtk.ICON_SIZE_BUTTON)
                self._searchentry.set_icon(sexy.ICON_ENTRY_SECONDARY, image)
                def pressed(entry, icon_pos, button):
                    if icon_pos == 0: # "primary"
                        self._searchmenu.popup(None, None, None, button, gtk.get_current_event_time())
                    elif icon_pos == 1: # "secondary"
                        self._searchentry.set_text("")
                        self.refreshPackages()
                self._searchentry.connect("icon-pressed", pressed)
            self._searchentry.connect("activate", lambda x: self.refreshPackages())
            self._searchentry.show()
            searchtable.attach(self._searchentry, 0, 1, 0, 1)

            self._searchmenu = gtk.Menu()
            self._searchname = gtk.CheckMenuItem(_("Automatic"))
            self._searchname.set_draw_as_radio(True)
            self._searchname.set_active(True)
            def search_automatic(item):
                self._searchdesc.set_active(not item.get_active())
                self.refreshPackages()
            self._searchname.connect("activate", search_automatic)
            self._searchname.show()
            self._searchmenu.append(self._searchname)
            self._searchdesc = gtk.CheckMenuItem(_("Description"))
            self._searchdesc.set_draw_as_radio(True)
            self._searchdesc.set_active(False)
            def search_description(item):
                self._searchname.set_active(not item.get_active())
                self.refreshPackages()
            self._searchdesc.connect("activate", search_description)
            self._searchdesc.show()
            self._searchmenu.append(self._searchdesc)
        else:
            self._searchbar = gtk.Alignment()
            self._searchbar.set(0, 0, 1, 1)
            self._searchbar.set_padding(3, 3, 0, 0)
            self._topvbox.pack_start(self._searchbar, False)

            searchvp = gtk.Viewport()
            searchvp.set_shadow_type(gtk.SHADOW_OUT)
            searchvp.show()
            self._searchbar.add(searchvp)

            searchtable = gtk.Table(1, 1)
            searchtable.set_row_spacings(5)
            searchtable.set_col_spacings(5)
            searchtable.set_border_width(5)
            searchtable.show()
            searchvp.add(searchtable)

            label = gtk.Label(_("Search:"))
            label.show()
            searchtable.attach(label, 0, 1, 0, 1, 0, 0)

            self._searchentry = gtk.Entry()
            self._searchentry.connect("activate", lambda x: self.refreshPackages())
            self._searchentry.show()
            searchtable.attach(self._searchentry, 1, 2, 0, 1)

            button = gtk.Button()
            button.set_relief(gtk.RELIEF_NONE)
            button.connect("clicked", lambda x: self.refreshPackages())
            button.show()
            searchtable.attach(button, 2, 3, 0, 1, 0, 0)
            image = gtk.Image()
            image.set_from_stock("gtk-find", gtk.ICON_SIZE_BUTTON)
            image.show()
            button.add(image)

            align = gtk.Alignment()
            align.set(1, 0, 0, 0)
            align.set_padding(0, 0, 10, 0)
            align.show()
            searchtable.attach(align, 3, 4, 0, 1, gtk.FILL, gtk.FILL)
            button = gtk.Button()
            button.set_size_request(20, 20)
            button.set_relief(gtk.RELIEF_NONE)
            button.connect("clicked", lambda x: self.toggleSearch())
            button.show()
            align.add(button)
            image = gtk.Image()
            image.set_from_stock("gtk-close", gtk.ICON_SIZE_MENU)
            image.show()
            button.add(image)

            hbox = gtk.HBox()
            hbox.set_spacing(10)
            hbox.show()
            searchtable.attach(hbox, 1, 2, 1, 2)

            self._searchmenu = None
            self._searchname = gtk.RadioButton(None, _("Automatic"))
            self._searchname.set_active(True)
            self._searchname.connect("clicked", lambda x: self.refreshPackages())
            self._searchname.show()
            hbox.pack_start(self._searchname, False)
            self._searchdesc = gtk.RadioButton(self._searchname, _("Description"))
            self._searchdesc.connect("clicked", lambda x: self.refreshPackages())
            self._searchdesc.show()
            hbox.pack_start(self._searchdesc, False)

        # Packages and information

        self._hpaned = gtk.HPaned()
        self._hpaned.show()
        self._topvbox.pack_start(self._hpaned)

        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self._hpaned.pack1(scrollwin, True)

        self._pg = gtk.TreeView()
        def group_selected(treeview):
            self.refreshPackages()
        self._pg.connect("cursor_changed", group_selected)
        self._pg.show()
        scrollwin.add(self._pg)

        selection = self._pg.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Group"), renderer, text=1)
        self._pg.append_column(column)

        self._vpaned = gtk.VPaned()
        self._vpaned.show()
        self._hpaned.pack2(self._vpaned, True)

        self._pv = GtkPackageView()
        self._pv.show()
        self._vpaned.pack1(self._pv, True)

        self._pi = GtkPackageInfo()
        self._pi.show()
        self._pv.connect("package_selected",
                         lambda x, y: self._pi.setPackage(y))
        self._pv.connect("package_activated",
                         lambda x, y: self.actOnPackages(y))
        self._pv.connect("package_popup", self.packagePopup)
        self._vpaned.pack2(self._pi, False)

        self._status = gtk.Statusbar()
        self._status.show()
        self._topvbox.pack_start(self._status, False)
        
        self._legend = GtkLegend()

    def showStatus(self, msg):
        self._status.pop(0)
        self._status.push(0, msg)
        while gtk.events_pending():
            gtk.main_iteration()

    def hideStatus(self):
        self._status.pop(0)
        while gtk.events_pending():
            gtk.main_iteration()

    def run(self, command=None, argv=None):
        self.setCatchExceptions(True)
        self.loadState()
        self._window.set_icon(getPixbuf("smart"))
        self._window.show()
        self._ctrl.reloadChannels()
        self._changeset = ChangeSet(self._ctrl.getCache())
        self._pi.setChangeSet(self._changeset)
        self._progress.hide()
        self.refreshPackages()
        gtk.main()
        self.saveState()
        self.setCatchExceptions(False)

    # Non-standard interface methods:

    def saveState(self):
        sysconf.set("gtk-size", self._window.get_size())
        #sysconf.set("gtk-position", self._window.get_position())
        sysconf.set("gtk-hpaned-position", self._hpaned.get_position())
        sysconf.set("gtk-vpaned-position", self._vpaned.get_position())

    def loadState(self):
        var = sysconf.get("gtk-size")
        if var is not None:
            self._window.set_size_request(*var)
        #var = sysconf.get("gtk-position")
        #if var is not None:
        #    self._window.move(*var)
        var = sysconf.get("gtk-hpaned-position")
        if var is not None:
            self._hpaned.set_position(var)
        var = sysconf.get("gtk-vpaned-position")
        if var is not None:
            self._vpaned.set_position(var)

    def getChangeSet(self):
        return self._changeset

    def updateSelected(self):
        self.updateChannels(selected=True)

    def updateChannels(self, selected=False, channels=None):
        if self._changeset is None:
            return
        if selected:
            aliases = GtkChannelSelector().show()
            channels = [channel for channel in self._ctrl.getChannels()
                        if channel.getAlias() in aliases]
            if not channels:
                return
        state = self._changeset.getPersistentState()
        self._ctrl.reloadChannels(channels, caching=NEVER)
        self._changeset.setPersistentState(state)
        self.refreshPackages()

    def rebuildCache(self):
        if self._changeset is None:
            return
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
            self._redomenuitem.set_property("sensitive", False)
            self._undomenuitem.set_property("sensitive", False)
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
        self._pv.getTreeView().expand_all()

    def collapsePackages(self):
        self._pv.getTreeView().collapse_all()

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

    def removeAuto(self):
        changeset = self._ctrl.markAndSweep()
        if changeset != self._changeset:
            if self.confirmChange(self._changeset, changeset):
                self.saveUndo()
                self._changeset.setState(changeset)
                self.changedMarks()
                self.applyChanges(confirm=True)
        else:
            self.showStatus(_("No automatic removals possible!"))

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

    def lockPackages(self, pkgs, lock):
        if not lock:
             for pkg in pkgs:
                  pkgconf.clearFlag("lock", pkg.name, "=", pkg.version)
             self._pv.queue_draw()
             self._pi.setPackage(pkgs[0])
        else:
             for pkg in pkgs:
                  pkgconf.setFlag("lock", pkg.name, "=", pkg.version)
             self._pv.queue_draw()
             self._pi.setPackage(pkgs[0])

    def lockAllPackages(self, pkgs, lock):
        if not lock:
             for pkg in pkgs:
                  pkgconf.clearFlag("lock", pkg.name)
             self._pv.queue_draw()
             self._pi.setPackage(pkgs[0])
        else:
             for pkg in pkgs:
                  pkgconf.setFlag("lock", pkg.name)
             self._pv.queue_draw()
             self._pi.setPackage(pkgs[0])

    def packagePopup(self, packageview, pkgs, event):

        menu = gtk.Menu()

        hasinstalled = bool([pkg for pkg in pkgs if pkg.installed
                             and self._changeset.get(pkg) is not REMOVE])
        hasnoninstalled = bool([pkg for pkg in pkgs if not pkg.installed
                                and self._changeset.get(pkg) is not INSTALL])

        image = gtk.Image()
        image.set_from_pixbuf(getPixbuf("package-install"))
        item = gtk.ImageMenuItem(_("Install"))
        item.set_image(image)
        item.connect("activate", lambda x: self.actOnPackages(pkgs, INSTALL))
        if not hasnoninstalled:
            item.set_sensitive(False)
        menu.append(item)

        image = gtk.Image()
        image.set_from_pixbuf(getPixbuf("package-reinstall"))
        item = gtk.ImageMenuItem(_("Reinstall"))
        item.set_image(image)
        item.connect("activate", lambda x: self.actOnPackages(pkgs, REINSTALL))
        if not hasinstalled:
            item.set_sensitive(False)
        menu.append(item)


        image = gtk.Image()
        image.set_from_pixbuf(getPixbuf("package-remove"))
        item = gtk.ImageMenuItem(_("Remove"))
        item.set_image(image)
        item.connect("activate", lambda x: self.actOnPackages(pkgs, REMOVE))
        if not hasinstalled:
            item.set_sensitive(False)
        menu.append(item)

        image = gtk.Image()
        if not hasinstalled:
            image.set_from_pixbuf(getPixbuf("package-available"))
        else:
            image.set_from_pixbuf(getPixbuf("package-installed"))
        item = gtk.ImageMenuItem(_("Keep"))
        item.set_image(image)
        item.connect("activate", lambda x: self.actOnPackages(pkgs, KEEP))
        if not [pkg for pkg in pkgs if pkg in self._changeset]:
            item.set_sensitive(False)
        menu.append(item)

        image = gtk.Image()
        image.set_from_pixbuf(getPixbuf("package-broken"))
        item = gtk.ImageMenuItem(_("Fix problems"))
        item.set_image(image)
        item.connect("activate", lambda x: self.actOnPackages(pkgs, FIX))
        if not hasinstalled:
            item.set_sensitive(False)
        menu.append(item)

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

        image = gtk.Image()
        if thislocked:
            item = gtk.ImageMenuItem(_("Unlock this version"))
            if not hasnoninstalled:
                image.set_from_pixbuf(getPixbuf("package-installed"))
            else:
                image.set_from_pixbuf(getPixbuf("package-available"))
            def unlock_this(x):
                self.lockPackages(pkgs, False)
            item.connect("activate", unlock_this)
        else:
            item = gtk.ImageMenuItem(_("Lock this version"))
            if not hasnoninstalled:
                image.set_from_pixbuf(getPixbuf("package-installed-locked"))
            else:
                image.set_from_pixbuf(getPixbuf("package-available-locked"))
            def lock_this(x):
                self.lockPackages(pkgs, True)
            item.connect("activate", lock_this)
        item.set_image(image)
        if inconsistent:
            item.set_sensitive(False)
        menu.append(item)

        image = gtk.Image()
        if alllocked:
            item = gtk.ImageMenuItem(_("Unlock all versions"))
            if not hasnoninstalled:
                image.set_from_pixbuf(getPixbuf("package-installed"))
            else:
                image.set_from_pixbuf(getPixbuf("package-available"))
            def unlock_all(x):
                self.lockAllPackages(pkgs, False)
            item.connect("activate", unlock_all)
        else:
            item = gtk.ImageMenuItem(_("Lock all versions"))
            if not hasnoninstalled:
                image.set_from_pixbuf(getPixbuf("package-installed-locked"))
            else:
                image.set_from_pixbuf(getPixbuf("package-available-locked"))
            def lock_all(x):
                self.lockAllPackages(pkgs, True)
            item.connect("activate", lock_all)
        item.set_image(image)
        if inconsistent:
            item.set_sensitive(False)
        menu.append(item)

        item = gtk.MenuItem(_("Priority"))
        def priority(x):
            GtkSinglePriority(self._window).show(pkgs[0])
            self._pi.setPackage(pkgs[0])
        item.connect("activate", priority)
        if len(pkgs) != 1:
            item.set_sensitive(False)
        menu.append(item)

        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)

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
                self._undomenuitem.set_property("sensitive", False)
            self._redo.insert(0, self._changeset.getPersistentState())
            self._redomenuitem.set_property("sensitive", True)
            self._changeset.setPersistentState(state)
            self.changedMarks()

    def redo(self):
        if self._redo:
            state = self._redo.pop(0)
            if not self._redo:
                self._redomenuitem.set_property("sensitive", False)
            self._undo.insert(0, self._changeset.getPersistentState())
            self._undomenuitem.set_property("sensitive", True)
            self._changeset.setPersistentState(state)
            self.changedMarks()

    def saveUndo(self):
        self._undo.insert(0, self._changeset.getPersistentState())
        del self._redo[:]
        del self._undo[20:]
        self._undomenuitem.set_property("sensitive", True)
        self._redomenuitem.set_property("sensitive", False)

    def setTreeStyle(self, mode):
        if mode != sysconf.get("package-tree"):
            if not sysconf.getReadOnly():
                sysconf.set("package-tree", mode)
            else:
                sysconf.set("package-tree", mode, weak=True)
            self.refreshPackages()

    def editChannels(self):
        if GtkChannels(self._window).show():
            self.rebuildCache()

    def editMirrors(self):
        GtkMirrors(self._window).show()

    def editFlags(self):
        GtkFlags(self._window).show()

    def editPriorities(self):
        GtkPriorities(self._window).show()

    def setBusy(self, flag):
        if flag:
            self._window.window.set_cursor(self._watch)
            while gtk.events_pending():
                gtk.main_iteration()
        else:
            self._window.window.set_cursor(None)

    def changedMarks(self):
        if "hide-unmarked" in self._filters:
            self.refreshPackages()
        else:
            self._pv.queue_draw()
        self._execmenuitem.set_property("sensitive", bool(self._changeset))
        self._clearmenuitem.set_property("sensitive", bool(self._changeset))

    def toggleSearch(self):
        if not isinstance(self._searchbar, gtk.ToolItem):
            visible = not self._searchbar.get_property('visible')
            self._searchbar.set_property('visible', visible)
        else:
            # always show the ToolItem
            visible = True
        self.refreshPackages()
        if visible:
            self._searchentry.grab_focus()

    def refreshPackages(self):
        if not self._ctrl:
            return

        self.setBusy(True)

        tree = sysconf.get("package-tree", "groups")
        ctrl = self._ctrl
        changeset = self._changeset

        self._pg.parent.set_property('visible', tree == "separate-groups")
        if self._pg.get_property('visible'):
            model = self._pg.get_model()
            if not model:
                packages = ctrl.getCache().getPackages()
                packagegroups = {}
                for pkg in packages:
                    for loader in pkg.loaders:
                        info = loader.getInfo(pkg)
                        group = info.getGroup()
                        if group in packagegroups:
                            packagegroups[group] += 1
                        else:
                            packagegroups[group] = 1

                groups = []
                names = {}
                all = "%s (%d)" % (_("All"), len(packages))
                for group, count in packagegroups.iteritems():
                     displayicon = None
                     displayname = "%s (%d)" % (group, count)
                     groups.append(displayname)
                     names[displayname] = group
                groups.sort()
                    
                model = gtk.ListStore(gobject.TYPE_STRING,
                                      gobject.TYPE_STRING)
                self._pg.set_model(model)
                iter = model.append()
                model.set(iter, 0, None)
                model.set(iter, 1, all)
                self._pg.get_selection().select_iter(iter)
                for group in groups:
                    iter = model.append()
                    model.set(iter, 0, names[group])
                    model.set(iter, 1, group)
                self._pg.queue_draw()

        columns = sysconf.get("package-columns", "name,version")
        self._pv.setVisibleColumns(columns.split(","))

        if self._searchbar.get_property("visible"):

            searcher = Searcher()
            dosearch = False
            if self._searchdesc.get_active():
                text = self._searchentry.get_text().strip()
                if text:
                    dosearch = True
                    searcher.addDescription(text)
                    searcher.addSummary(text)
            else:
                try:
                    tokens = shlex.split(self._searchentry.get_text())
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
            elif isinstance(self._searchbar, gtk.ToolItem):
                packages = ctrl.getCache().getPackages()
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
            if "hide-non-newest" in filters:
                newest = {}
                for pkg in packages:
                    if pkg.name in newest:
                        if pkg > newest[pkg.name]:
                            newest[pkg.name] = pkg
                    else:
                        newest[pkg.name] = pkg
                packages = [pkg for pkg in packages if pkg == newest[pkg.name]]
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

        elif tree == "separate-groups":
            showgroups = {}
            selection = self._pg.get_selection()
            model, paths = selection.get_selected_rows()
            for path in paths:
                iter = model.get_iter(path)
                value = model.get_value(iter, 0)
                showgroups[value] = True
            if showgroups and None not in showgroups:
                newpackages = []
                done = {}
                for pkg in packages:
                    for loader in pkg.loaders:
                        info = loader.getInfo(pkg)
                        group = info.getGroup()
                        donetuple = (group, pkg)
                        if donetuple not in done:
                            done[donetuple] = True
                            if group in showgroups:
                                newpackages.append(pkg)
                groups = newpackages
            else:
                groups = packages

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

        packages = ctrl.getCache().getPackages()
        self.showStatus(_("%d packages, %d installed") %
            (len(packages), len([pkg for pkg in packages if pkg.installed])))

        self.setBusy(False)

    def showAbout(widget):
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
            """Canonical Ltd. - Funding Smart up to November of 2009.""",
            """Unity Linux - Smart development and deployment support.""",
            """And many others - Check our website for the complete list.""",
            ]
        website = "http://smartpm.org/"

        if gtk.pygtk_version < (2,6,0):
             dialog = gtk.MessageDialog(buttons=gtk.BUTTONS_CLOSE)
             dialog.set_markup("<b>Smart Package Manager %s</b>\n"
                               "<small>(C) %s</small>\n" % (VERSION, copyright) +
                               "<small>%s</small>\n" % license.replace(" " * 12, "") +
                               "<span>%s</span>\n" % "\n".join(credits) +
                               "\n<tt>%s</tt>" % website)
             dialog.run()
             dialog.destroy()
             return

        aboutdialog = gtk.AboutDialog()
        aboutdialog.set_name("Smart Package Manager")
        aboutdialog.set_version(VERSION)
        aboutdialog.set_copyright(copyright)
        aboutdialog.set_authors(credits)
        aboutdialog.set_license(license)
        aboutdialog.set_website(website)
        aboutdialog.run()
        aboutdialog.destroy()

# vim:ts=4:sw=4:et

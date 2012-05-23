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
from smart.interfaces.gtk.packageview import GtkPackageView
from smart.interfaces.gtk import getPixbuf
from smart.util.strtools import sizeToStr
from smart.report import Report
from smart import *
from gi.repository import GObject, Gtk

class GtkChanges(Gtk.Window):

    def __init__(self):
        GObject.GObject.__init__(self)

        self.set_icon(getPixbuf("smart"))
        self.set_title(_("Change Summary"))
        self.set_modal(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_geometry_hints(min_width=600, min_height=400)
        def delete(widget, event):
            Gtk.main_quit()
            return True
        self.connect("delete-event", delete)

        self._vbox = Gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self.add(self._vbox)

        self._label = Gtk.Label()
        self._vbox.pack_start(self._label, False, True, 0)

        self._pv = GtkPackageView()
        self._pv.getTreeView().set_headers_visible(False)
        self._pv.setExpandPackage(True)
        self._pv.show()
        self._vbox.pack_start(self._pv, True, True, 0)

        self._sizelabel = Gtk.Label()
        self._vbox.pack_start(self._sizelabel, False, True, 0)

        self._confirmbbox = Gtk.HButtonBox()
        self._confirmbbox.set_spacing(10)
        self._confirmbbox.set_layout(Gtk.ButtonBoxStyle.END)
        self._vbox.pack_start(self._confirmbbox, False, True, 0)

        self._cancelbutton = Gtk.Button(stock="gtk-cancel")
        self._cancelbutton.show()
        self._cancelbutton.connect("clicked", lambda x: Gtk.main_quit())
        self._confirmbbox.pack_start(self._cancelbutton, True, True, 0)

        self._okbutton = Gtk.Button(stock="gtk-ok")
        self._okbutton.show()
        def clicked(x):
            self._result = True
            Gtk.main_quit()
        self._okbutton.connect("clicked", clicked)
        self._confirmbbox.pack_start(self._okbutton, True, True, 0)

        self._closebbox = Gtk.HButtonBox()
        self._closebbox.set_spacing(10)
        self._closebbox.set_layout(Gtk.ButtonBoxStyle.END)
        self._vbox.pack_start(self._closebbox, False, True, 0)

        self._closebutton = Gtk.Button(stock="gtk-close")
        self._closebutton.show()
        self._closebutton.connect("clicked", lambda x: Gtk.main_quit())
        self._closebbox.pack_start(self._closebutton, True, True, 0)

    def showChangeSet(self, changeset, keep=None, confirm=False, label=None):

        report = Report(changeset)
        report.compute()
        
        class Sorter(str):
            ORDER = [_("Remove"), _("Downgrade"), _("Reinstall"),
                     _("Install"), _("Upgrade")]
            def _index(self, s):
                i = 0
                for os in self.ORDER:
                    if os.startswith(s):
                        return i
                    i += 1
                return i
            def __cmp__(self, other):
                return cmp(self._index(str(self)), self._index(str(other)))
            def __lt__(self, other):
                return cmp(self, other) < 0

        packages = {}

        if report.install:
            install = {}
            reinstall = {}
            upgrade = {}
            downgrade = {}
            lst = list(report.install.keys())
            lst.sort()
            for pkg in lst:
                package = {}
                done = {}
                if pkg in report.upgrading:
                    for upgpkg in report.upgrading[pkg]:
                        package.setdefault(_("Upgrades"), []).append(upgpkg)
                        done[upgpkg] = True
                if pkg in report.downgrading:
                    for dwnpkg in report.downgrading[pkg]:
                        package.setdefault(_("Downgrades"), []).append(dwnpkg)
                        done[dwnpkg] = True
                if pkg in report.requires:
                    for reqpkg in report.requires[pkg]:
                        package.setdefault(_("Requires"), []).append(reqpkg)
                if pkg in report.requiredby:
                    for reqpkg in report.requiredby[pkg]:
                        package.setdefault(_("Required By"), []).append(reqpkg)
                if pkg in report.conflicts:
                    for cnfpkg in report.conflicts[pkg]:
                        if cnfpkg in done:
                            continue
                        package.setdefault(_("Conflicts"), []).append(cnfpkg)
                if pkg.installed:
                    reinstall[pkg] = package
                elif pkg in report.upgrading:
                    upgrade[pkg] = package
                elif pkg in report.downgrading:
                    downgrade[pkg] = package
                else:
                    install[pkg] = package
            if reinstall:
                packages[Sorter(_("Reinstall (%d)") % len(reinstall))] = \
                                                                    reinstall
            if install:
                packages[Sorter(_("Install (%d)") % len(install))] = install
            if upgrade:
                packages[Sorter(_("Upgrade (%d)") % len(upgrade))] = upgrade
            if downgrade:
                packages[Sorter(_("Downgrade (%d)") % len(downgrade))] = \
                                                                    downgrade

        if report.removed:
            remove = {}
            lst = list(report.removed.keys())
            lst.sort()
            for pkg in lst:
                package = {}
                done = {}
                if pkg in report.requires:
                    for reqpkg in report.requires[pkg]:
                        package.setdefault(_("Requires"), []).append(reqpkg)
                if pkg in report.requiredby:
                    for reqpkg in report.requiredby[pkg]:
                        package.setdefault(_("Required By"), []).append(reqpkg)
                if pkg in report.conflicts:
                    for cnfpkg in report.conflicts[pkg]:
                        if cnfpkg in done:
                            continue
                        package.setdefault(_("Conflicts"), []).append(cnfpkg)
                remove[pkg] = package
            if remove:
                packages[Sorter(_("Remove (%d)") % len(report.removed))] = \
                                                                        remove

        if keep:
            packages[Sorter(_("Keep (%d)") % len(keep))] = keep

        dsize = report.getDownloadSize() - report.getCachedSize()
        size = report.getInstallSize() - report.getRemoveSize()
        sizestr = ""
        if dsize:
            sizestr += _("%s of package files are needed. ") % sizeToStr(dsize)
        if size > 0:
            sizestr += _("%s will be used.") % sizeToStr(size)
        elif size < 0:
            size *= -1
            sizestr += _("%s will be freed.") % sizeToStr(size)
        if dsize or size:
            self._sizelabel.set_text(sizestr)
            self._sizelabel.show()
        else:
            self._sizelabel.hide()

        if confirm:
            self._confirmbbox.show()
            self._closebbox.hide()
        else:
            self._closebbox.show()
            self._confirmbbox.hide()

        if label:
            self._label.set_text(label)
            self._label.show()
        else:
            self._label.hide()

        self._pv.setPackages(packages, changeset)

        # Expand first level
        self._pv.setExpanded([(x,) for x in packages])

        self._result = False
        self.show()
        Gtk.main()
        self.hide()

        return self._result

# vim:ts=4:sw=4:et

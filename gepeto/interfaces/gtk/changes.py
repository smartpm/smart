#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Gepeto.
#
# Gepeto is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gepeto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gepeto; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from gepeto.interfaces.gtk.packageview import GtkPackageView
from gepeto.interfaces.gtk import getPixbuf
from gepeto.report import Report
import gobject, gtk

class GtkChanges(object):

    def __init__(self):

        self._window = gtk.Window()
        self._window.set_title("Change Summary")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=600, min_height=400)
        def delete(widget, event):
            gtk.main_quit()
            return True
        self._window.connect("delete-event", delete)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self._window.add(self._vbox)

        self._label = gtk.Label()
        self._vbox.pack_start(self._label, expand=False)

        self._pv = GtkPackageView()
        self._pv.getTreeView().set_headers_visible(False)
        self._pv.setExpandPackage(True)
        self._pv.show()
        self._vbox.pack_start(self._pv)

        self._confirmbbox = gtk.HButtonBox()
        self._confirmbbox.set_spacing(10)
        self._confirmbbox.set_layout(gtk.BUTTONBOX_END)
        self._vbox.pack_start(self._confirmbbox, expand=False)

        self._okbutton = gtk.Button(stock="gtk-ok")
        self._okbutton.show()
        def clicked(x):
            self._result = True
            gtk.main_quit()
        self._okbutton.connect("clicked", clicked)
        self._confirmbbox.pack_start(self._okbutton)

        self._cancelbutton = gtk.Button(stock="gtk-cancel")
        self._cancelbutton.show()
        self._cancelbutton.connect("clicked", lambda x: gtk.main_quit())
        self._confirmbbox.pack_start(self._cancelbutton)

        self._closebbox = gtk.HButtonBox()
        self._closebbox.set_spacing(10)
        self._closebbox.set_layout(gtk.BUTTONBOX_END)
        self._vbox.pack_start(self._closebbox, expand=False)

        self._closebutton = gtk.Button(stock="gtk-close")
        self._closebutton.show()
        self._closebutton.connect("clicked", lambda x: gtk.main_quit())
        self._closebbox.pack_start(self._closebutton)

    def showChangeSet(self, changeset, keep=None, confirm=False, label=None):

        report = Report(changeset)
        report.compute()
        
        class Sorter(str):
            ORDER = ["Remove", "Downgrade", "Reinstall", "Install", "Upgrade"]
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
            lst = report.install.keys()
            lst.sort()
            for pkg in lst:
                package = {}
                done = {}
                if pkg in report.upgrading:
                    for upgpkg in report.upgrading[pkg]:
                        package.setdefault("Upgrades", []).append(upgpkg)
                        done[upgpkg] = True
                if pkg in report.downgrading:
                    for dwnpkg in report.downgrading[pkg]:
                        package.setdefault("Downgrades", []).append(dwnpkg)
                        done[dwnpkg] = True
                if pkg in report.requires:
                    for reqpkg in report.requires[pkg]:
                        package.setdefault("Requires", []).append(reqpkg)
                if pkg in report.requiredby:
                    for reqpkg in report.requiredby[pkg]:
                        package.setdefault("Required By", []).append(reqpkg)
                if pkg in report.conflicts:
                    for cnfpkg in report.conflicts[pkg]:
                        if cnfpkg in done:
                            continue
                        package.setdefault("Conflicts", []).append(cnfpkg)
                if pkg.installed:
                    reinstall[pkg] = package
                elif pkg in report.upgrading:
                    upgrade[pkg] = package
                elif pkg in report.downgrading:
                    downgrade[pkg] = package
                else:
                    install[pkg] = package
            if reinstall:
                packages[Sorter("Reinstall (%d)" % len(reinstall))] = reinstall
            if install:
                packages[Sorter("Install (%d)" % len(install))] = install
            if upgrade:
                packages[Sorter("Upgrade (%d)" % len(upgrade))] = upgrade
            if downgrade:
                packages[Sorter("Downgrade (%d)" % len(downgrade))] = downgrade

        if report.remove:
            remove = {}
            lst = report.remove.keys()
            lst.sort()
            for pkg in lst:
                package = {}
                done = {}
                if pkg in report.upgraded or pkg in report.downgraded:
                    continue
                if pkg in report.requires:
                    for reqpkg in report.requires[pkg]:
                        package.setdefault("Requires", []).append(reqpkg)
                if pkg in report.requiredby:
                    for reqpkg in report.requiredby[pkg]:
                        package.setdefault("Required By", []).append(reqpkg)
                if pkg in report.conflicts:
                    for cnfpkg in report.conflicts[pkg]:
                        if cnfpkg in done:
                            continue
                        package.setdefault("Conflicts", []).append(cnfpkg)
                remove[pkg] = package
            if remove:
                packages[Sorter("Remove (%d)" % len(report.remove))] = remove

        if keep:
            packages["Keep (%d)" % len(keep)] = keep

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
        self._window.show()
        gtk.main()
        self._window.hide()

        return self._result

# vim:ts=4:sw=4:et

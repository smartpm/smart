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
from smart.interfaces.qt.packageview import QtPackageView
from smart.interfaces.qt import getPixmap, centerWindow
from smart.util.strtools import sizeToStr
from smart.report import Report
from smart import *
import qt

class QtChanges(qt.QDialog):

    def __init__(self, parent=None):
        qt.QDialog.__init__(self, parent)

        self.setIcon(getPixmap("smart"))
        self.setCaption(_("Change Summary"))
        self.setModal(True)
        self.setMinimumSize(600, 400)
        centerWindow(self)
        
        self._vbox = qt.QVBoxLayout(self)
        self._vbox.setMargin(10)
        self._vbox.setSpacing(10)

        self._label = qt.QLabel(self)
        self._vbox.addWidget(self._label)

        self._pv = QtPackageView(self)
        self._pv.getTreeView().header().hide()
        self._pv.setExpandPackage(True)
        self._pv.show()
        self._vbox.addWidget(self._pv)

        self._sizelabel = qt.QLabel("", self)
        self._vbox.addWidget(self._sizelabel)

        self._confirmbbox = qt.QHBox(self)
        self._confirmbbox.setSpacing(10)
        self._confirmbbox.layout().addStretch(1)
        self._vbox.addWidget(self._confirmbbox)

        self._cancelbutton = qt.QPushButton(_("Cancel"), self._confirmbbox)
        qt.QObject.connect( self._cancelbutton, qt.SIGNAL("clicked()"), self, qt.SLOT("reject()"))
        self._okbutton = qt.QPushButton(_("OK"), self._confirmbbox)
        qt.QObject.connect( self._okbutton, qt.SIGNAL("clicked()"), self, qt.SLOT("accept()"))

        self._closebbox = qt.QHBox(self)
        self._closebbox.setSpacing(10)
        self._closebbox.layout().addStretch(1)
        self._vbox.addWidget(self._closebbox)

        self._closebutton = qt.QPushButton(_("Close"), self._closebbox)
        qt.QObject.connect( self._closebutton, qt.SIGNAL("clicked()"), self, qt.SLOT("close()"))
        
    def showChangeSet(self, changeset, keep=None, confirm=False, label=None):

        report = Report(changeset)
        report.compute()
        
        class Sorter(unicode):
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
                return cmp(self._index(unicode(self)), self._index(unicode(other)))
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
            lst = report.removed.keys()
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

        dsize = report.getDownloadSize()
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
            self._sizelabel.setText(sizestr)
            self._sizelabel.show()
        else:
            self._sizelabel.hide()

        if confirm:
            self._confirmbbox.show()
            self._closebbox.hide()
            self._okbutton.setDefault(True)
        else:
            self._closebbox.show()
            self._confirmbbox.hide()
            self._closebutton.setDefault(True)

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
        dialogResult = self.exec_loop()
        self._result = (dialogResult == qt.QDialog.Accepted)

        return self._result

# vim:ts=4:sw=4:et

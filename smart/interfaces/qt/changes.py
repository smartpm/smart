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
from smart.interfaces.qt import getPixmap
from smart.util.strtools import sizeToStr
from smart.report import Report
from smart import *
from qt import *
#import gobject, gtk

class QtChanges(QDialog):
    def __init__(self, parent = None, name = None,  fl= 0):
	    QDialog.__init__(self,parent,name,fl)
	    if not name:
		self.setName("Change Summary:")
		self.createInterface()

    def confirmClicked(self):
	    self._result = True
            self.close()
	
    def closeClicked(self):
	    self.close()	

    def createInterface(self):
            #self.setIcon(getPixbuf("smart"))
            self._vbox = QVBoxLayout(self)
	    self._label = QLabel(self)
	    self._label.setText("Change Summary:")

	    self._packageListView = QtPackageView(self)
	    self._pv = self._packageListView 
	    #self._packageListView = QListView(self)
	    #self._packageListView.addColumn("colonna 1")
	    #for i in range(30):
	        #item = QListViewItem(self._packageListView, "ciao "+ str(i))
		#self._packageListView.insertItem(item)
			

	    self._sizelabel = QLabel("label spazio", self)
	    #####spazio x i bottoni########
	    self._confirmbbox = QHBoxLayout(self)
	    self._cancelbutton = QPushButton("Cancel", self)
	    self._confirmbutton = QPushButton("Confirm", self)


	    #QObject.connect( self._confirmbutton, SIGNAL("clicked()"), self.confirmClicked)
	    QObject.connect( self._confirmbutton, SIGNAL("clicked()"), self, SLOT("accept()"))
	    #QObject.connect( self._cancelbutton, SIGNAL("clicked()"), self.closeClicked)
	    QObject.connect( self._cancelbutton, SIGNAL("clicked()"), self, SLOT("reject()"))
		
	    spacer = QSpacerItem(160,20)
	    self._confirmbbox.addItem(spacer)
	    self._confirmbbox.addWidget(self._cancelbutton)
	    self._confirmbbox.addWidget(self._confirmbutton)
		
	    ####layout#########
	    self._vbox.addWidget(self._label)
	    self._vbox.addWidget(self._packageListView)
	    self._vbox.addWidget(self._sizelabel)
		
	    
	    self._vbox.addItem(self._confirmbbox)

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
            self._confirmbutton.show()
            #self._cancelbutton.hide()
        else:
            self._cancelbutton.show()
            #self._confirmbutton.hide()

        if label:
            self._label.set_text(label)
            self._label.show()
        else:
            self._label.hide()

        self._pv.setPackages(packages, changeset)

        # Expand first level
        #self._pv.setExpanded([(x,) for x in packages])

        self._result = False

	dialogResult = self.exec_loop()
	if dialogResult == QDialog.Accepted:
		self._result = True
	else:
		self._result = False
        return self._result

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    change = QtChanges()
    change.show()
    app.connect(app, SIGNAL("lastWindowClosed()"), app, SLOT("quit()"))
    app.exec_loop()
# vim:ts=4:sw=4:et

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
from smart.interfaces.qt4 import getPixmap, centerWindow
from smart import *
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import re

TARGETRE = re.compile(r"^\s*(\S+?)\s*(?:([<>=]+)\s*(\S+))?\s*$")

class QtFlags(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(None)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("Flags"))
        self._window.setModal(True)
        
        self._window.setMinimumSize(600, 400)

        layout = QtGui.QVBoxLayout(self._window)
        layout.setResizeMode(QtGui.QLayout.FreeResize)

        topvbox = qt.QVBox(self._window)
        topvbox.setMargin(10)
        topvbox.setSpacing(10)
        topvbox.show()

        layout.addWidget(topvbox)

        tophbox = qt.QHBox(topvbox)
        tophbox.setSpacing(20)
        tophbox.show()

        # Left side
        vbox = qt.QVGroupBox(tophbox)
        vbox.setInsideSpacing(10)
        vbox.show()

        self._flagsview = QtGui.QTableWidget(vbox)
        self._flagsview.show()

        QtCore.QObject.connect(self._flagsview, QtCore.SIGNAL("selectionChanged()"), self.flagSelectionChanged)

        self._flagsview.addColumn(_("Flags"))

        bbox = qt.QHBox(vbox)
        bbox.setMargin(5)
        bbox.setSpacing(10)
        bbox.show()

        button = qt.QPushButton(_("New"), bbox)
        button.setEnabled(True)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-add")))
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.newFlag)
        self._newflag = button

        button = QtGui.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-delete")))
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.delFlag)
        self._delflag = button

        # Right side
        vbox = qt.QVGroupBox(tophbox)
        vbox.setInsideSpacing(10)
        vbox.show()

        self._targetsview = QtGui.QTableWidget(vbox)
        self._targetsview.show()

        QtCore.QObject.connect(self._targetsview, QtCore.SIGNAL("selectionChanged()"), self.targetSelectionChanged)

        self._targetsview.addColumn(_("Targets"))

        bbox = qt.QHBox(vbox)
        bbox.setMargin(5)
        bbox.setSpacing(10)
        bbox.show()

        button = QtGui.QPushButton(_("New"), bbox)
        button.setEnabled(False)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-add")))
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.newTarget)
        self._newtarget = button

        button = QtGui.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-delete")))
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.delTarget)
        self._deltarget = button


        # Bottom
        sep = QtGui.QFrame(topvbox)
        sep.setFrameShape(QtGui.QFrame.HLine)
        sep.setFrameShadow(QtGui.QFrame.Sunken)
        sep.show()

        bbox = qt.QHBox(topvbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtGui.QPushButton(_("Close"), bbox)
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        
        button.setDefault(True)

    def fillFlags(self):
        self._flagsview.clear()
        flaglst = pkgconf.getFlagNames()
        flaglst.sort()
        for flag in flaglst:
            qt.QListViewItem(self._flagsview).setText(0, flag)
    
    def fillTargets(self):
        self._targetsview.clear()
        if self._flag:
            names = pkgconf.getFlagTargets(self._flag)
            namelst = names.keys()
            namelst.sort()
            for name in namelst:
                for relation, version in names[name]:
                    if relation and version:
                        item = QtGui.QTableWidgetItem(self._targetsview)
                        item.setText(0, "%s %s %s" % (name, relation, version))
                    else:
                        QtGui.QTableWidgetItem(self._targetsview).setText(0, name)

    def show(self):
        self.fillFlags()
        self._window.show()
        centerWindow(self._window)
        self._window.raiseW()
        self._window.exec_loop()
        self._window.hide()

    def newFlag(self):
        flag = FlagCreator(self._window).show()
        if flag:
            if pkgconf.flagExists(flag):
                iface.error(_("Flag already exists!"))
            else:
                pkgconf.createFlag(flag)
                self.fillFlags()

    def newTarget(self):
        target = TargetCreator(self._window).show()
        if target:
            m = TARGETRE.match(target)
            if m:
                name, relation, version = m.groups()
                pkgconf.setFlag(self._flag, name, relation, version)
            self.fillTargets()

    def delFlag(self):
        item = self._flagsview.selectedItem()
        if item:
            pkgconf.clearFlag(self._flag)
            self.fillFlags()
            self.fillTargets()

    def delTarget(self):
        item = self._targetsview.selectedItem()
        if item:
            target = str(item.text(0))
            m = TARGETRE.match(target)
            if not m:
                iface.error(_("Invalid target!"))
            else:
                name, relation, version = m.groups()
                pkgconf.clearFlag(self._flag, name, relation, version)
                if not pkgconf.flagExists(self._flag):
                    self.fillFlags()
                else:
                    self.fillTargets()

    def flagEdited(self, cell, row, newtext):
        model = self._flagsmodel
        iter = model.get_iter_from_string(row)
        oldtext = model.get_value(iter, 0)
        if newtext != oldtext:
            if pkgconf.flagExists(newtext):
                iface.error(_("Flag already exists!"))
            else:
                pkgconf.renameFlag(oldtext, newtext)
                model.set_value(iter, 0, newtext)

    def targetEdited(self, cell, row, newtext):
        model = self._targetsmodel
        iter = model.get_iter_from_string(row)
        oldtext = model.get_value(iter, 0)
        if newtext != oldtext:
            m = TARGETRE.match(oldtext)
            if not m:
                iface.error(_("Invalid target!"))
            else:
                oldname, oldrelation, oldversion = m.groups()
                m = TARGETRE.match(newtext)
                if not m:
                    iface.error(_("Invalid target!"))
                else:
                    newname, newrelation, newversion = m.groups()
                    pkgconf.clearFlag(self._flag, oldname,
                                      oldrelation, oldversion)
                    pkgconf.setFlag(self._flag, newname,
                                    newrelation, newversion)
                    if newrelation and newversion:
                        model.set_value(iter, 0, "%s %s %s" %
                                        (newname, newrelation, newversion))
                    else:
                        model.set_value(iter, 0, newname)

    def flagSelectionChanged(self):
        item = self._flagsview.selectedItem()
        self._delflag.setEnabled(bool(item))
        self._newtarget.setEnabled(bool(item))
        if item:
            self._flag = str(item.text(0))
        else:
            self._flag = None
        self.fillTargets()

    def targetSelectionChanged(self):
        item = self._targetsview.selectedItem()
        self._deltarget.setEnabled(bool(item))

class FlagCreator(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Flag"))
        self._window.setModal(True)

        #self._window.setMinimumSize(600, 400)

        vbox = qt.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        table = qt.QGrid(2, vbox)
        table.setSpacing(10)
        
        label = QtGui.QLabel(_("Name:"), table)

        self._flag = QtGui.QLineEdit(table)
        self._flag.setMaxLength(20)
        self._flag.show()

        sep = QtGui.QFrame(vbox)
        sep.setFrameShape(QtGui.QFrame.HLine)
        sep.setFrameShadow(QtGui.QFrame.Sunken)
        sep.show()

        bbox = QtGui.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtGui.QPushButton(bbox.tr("OK"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))

        button = QtGui.QPushButton(bbox.tr("Cancel"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("reject()"))

        vbox.adjustSize()
        self._window.adjustSize()

    def show(self):

        self._window.show()
        self._window.raiseW()
        self._window.setActiveWindow()

        while True:
            self._result = self._window.exec_loop()
            if self._result == QtGui.QDialog.Accepted:
                flag = str(self._flag.text()).strip()
                if not flag:
                    iface.error(_("No flag name provided!"))
                    continue
                break
            flag = None
            break

        self._window.hide()

        return flag

class TargetCreator(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Target"))
        self._window.setModal(True)

        #self._window.setMinimumSize(600, 400)

        vbox = qt.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        table = qt.QGrid(2, vbox)
        table.setSpacing(10)
        table.show()
        
        label = QtGui.QLabel(_("Target:"), table)

        self._target = QtGui.QLineEdit(table)
        self._target.setMaxLength(40)
        self._target.show()

        blank = QtGui.QWidget(table)

        label = QtGui.QLabel(_("Examples: \"pkgname\", \"pkgname = 1.0\" or "
                            "\"pkgname <= 1.0\""), table)

        sep = QtGui.QFrame(vbox)
        sep.setFrameShape(QtGui.QFrame.HLine)
        sep.setFrameShadow(QtGui.QFrame.Sunken)
        sep.show()

        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtGui.QPushButton(bbox.tr("OK"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))

        button = QtGui.QPushButton(bbox.tr("Cancel"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("reject()"))

        vbox.adjustSize()
        self._window.adjustSize()

    def show(self):

        self._window.show()
        self._window.raiseW()
        self._window.setActiveWindow()

        while True:
            self._result = self._window.exec_loop()
            if self._result == QtGui.QDialog.Accepted:
                target = str(self._target.text()).strip()
                if not target:
                    iface.error(_("No target provided!"))
                    continue
                if ('"' in target or ',' in target or
                    not TARGETRE.match(target)):
                    iface.error(_("Invalid target!"))
                    continue
                break
            target = None
            break

        self._window.hide()

        return target

# vim:ts=4:sw=4:et

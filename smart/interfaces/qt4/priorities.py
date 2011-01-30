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
from smart.channel import getChannelInfo
from smart import *
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

class TextListViewItem(QtGui.QTableWidgetItem):
    def __init__(self, parent):
        QtGui.QTableWidgetItem.__init__(self)
        self._text = {}
        self._oldtext = {}

    def setText(self, col, text):
        QtGui.QTableWidgetItem.setText(self, text)
        if col in self._text:
            self._oldtext[col] = self._text[col]
        self._text[col] = text

    def oldtext(self, col):
        return self._oldtext.get(col, None)

class QtPriorities(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(None)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("Priorities"))
        #self._window.setModal(True)

        self._window.setMinimumSize(600, 400)

        layout = QtGui.QVBoxLayout(self._window)
        #layout.setResizeMode(QtGui.QLayout.FreeResize)

        vbox = QtGui.QWidget(self._window)
        QtGui.QVBoxLayout(vbox)
        vbox.layout().setMargin(10)
        vbox.layout().setSpacing(10)
        vbox.show()

        layout.addWidget(vbox)

        self._treeview = QtGui.QTableWidget(vbox)
        #self._treeview.setAllColumnsShowFocus(True)
        self._treeview.show()
        vbox.layout().addWidget(self._treeview)

        QtCore.QObject.connect(self._treeview, QtCore.SIGNAL("itemChanged(QTableWidgetItem *, int)"), self.itemChanged)
        QtCore.QObject.connect(self._treeview, QtCore.SIGNAL("selectionChanged()"), self.selectionChanged)

        #self._treeview.addColumn(_("Package Name"))
        #self._treeview.addColumn(_("Channel Alias"))
        #self._treeview.addColumn(_("Priority"))

        bbox = QtGui.QWidget(vbox)
        QtGui.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()
        vbox.layout().addWidget(bbox)

        button = QtGui.QPushButton(_("New"), bbox)
        button.setEnabled(True)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-add")))
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.newPriority)
        self._newpriority = button
        bbox.layout().addWidget(button)

        button = QtGui.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-delete")))
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.delPriority)
        self._delpriority = button
        bbox.layout().addWidget(button)

        button = QtGui.QPushButton(_("Close"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        bbox.layout().addWidget(button)
        
        button.setDefault(True)
        vbox.adjustSize()

    def fill(self):
        self._treeview.clear()
        priorities = sysconf.get("package-priorities", {})
        prioritieslst = priorities.items()
        prioritieslst.sort()
        for name, pkgpriorities in prioritieslst:
            aliaslst = pkgpriorities.items()
            aliaslst.sort()
            for alias, priority in aliaslst:
                 item = TextListViewItem(self._treeview)
                 item.setText(0, name)
                 item.setText(1, alias or "*")
                 item.setText(2, str(priority))
                 #item.setRenameEnabled(0, True)
                 #item.setRenameEnabled(1, True)
                 #item.setRenameEnabled(2, True)

    def show(self):
        self.fill()
        self._window.show()
        centerWindow(self._window)
        self._window.raise_()
        self._window.exec_()
        self._window.hide()

    def newPriority(self):
        name, alias, priority = PriorityCreator(self._window).show()
        if name:
            if sysconf.has(("package-priorities", name, alias)):
                iface.error(_("Name/alias pair already exists!"))
            else:
                sysconf.set(("package-priorities", name, alias), int(priority))
                self.fill()

    def delPriority(self):
        item = self._treeview.selectedItem()
        if item:
            name = str(item.text(0))
            alias = str(item.text(1))
            if alias == "*":
                alias = None
            sysconf.remove(("package-priorities", name, alias))
        self.fill()

    def selectionChanged(self):
        item = self._treeview.selectedItem()
        self._delpriority.setEnabled(bool(item))

    def itemChanged(self, item, col):
        newtext = item.text(col)
        newtext = str(newtext).strip()
        if col == 1:
            if newtext == "*":
                newtext = ""
        oldtext = item.oldtext(col)
        if newtext != oldtext:
            if col == 0:
                alias = str(item.text(0))
                if alias == "*":
                    alias = None
                priority = str(item.text(2))
                if not newtext:
                    pass
                elif sysconf.has(("package-priorities", newtext, alias)):
                    iface.error(_("Name/alias pair already exists!"))
                else:
                    sysconf.set(("package-priorities", newtext, alias),
                                int(priority))
                    sysconf.remove(("package-priorities", oldtext, alias))
            elif col == 1:
                name = item.text(0)
                priority = item.text(2)
                if sysconf.has(("package-priorities", name, newtext)):
                    iface.error(_("Name/alias pair already exists!"))
                else:
                    sysconf.move(("package-priorities", name, oldtext),
                                 ("package-priorities", name, newtext))
                    item.setText(col, newtext or "*")
            elif col == 2:
                if newtext:
                    name = str(item.text(0))
                    alias = str(item.text(1))
                    if alias == "*":
                        alias = None
                    try:
                        sysconf.set(("package-priorities", name, alias),
                                    int(newtext))
                    except ValueError:
                        item.setText(col, oldtext)
                        iface.error(_("Invalid priority!"))

class PriorityCreator(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("New Package Priority"))
        self._window.setModal(True)

        #self._window.setMinimumSize(600, 400)

        vbox = QtGui.QWidget(self._window)
        QtGui.QVBoxLayout(vbox)
        vbox.layout().setMargin(10)
        vbox.layout().setSpacing(10)
        vbox.show()

        table = QtGui.QWidget(self._window)
        QtGui.QGridLayout(table)
        table.layout().setSpacing(10)
        table.show()
        vbox.layout().addWidget(table)
        
        label = QtGui.QLabel(_("Package Name:"), table)
        table.layout().addWidget(label)

        self._name = QtGui.QLineEdit(table)
        self._name.show()
        table.layout().addWidget(self._name)

        label = QtGui.QLabel(_("Channel Alias:"), table)
        table.layout().addWidget(label)

        self._alias = QtGui.QLineEdit(table)
        self._alias.setText("*")
        self._alias.show()
        table.layout().addWidget(self._alias)

        label = QtGui.QLabel(_("Priority:"), table)
        table.layout().addWidget(label)

        self._priority = QtGui.QSpinBox(table)
        self._priority.setSingleStep(1)
        self._priority.setRange(-100000,+100000)
        self._priority.show()
        table.layout().addWidget(self._priority)

        sep = QtGui.QFrame(vbox)
        sep.setFrameShape(QtGui.QFrame.HLine)
        sep.setFrameShadow(QtGui.QFrame.Sunken)
        sep.show()
        vbox.layout().addWidget(sep)

        bbox = QtGui.QWidget(vbox)
        QtGui.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()
        vbox.layout().addWidget(bbox)

        button = QtGui.QPushButton(_("Cancel"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("reject()"))
        bbox.layout().addWidget(button)

        button = QtGui.QPushButton(_("OK"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        bbox.layout().addWidget(button)

        button.setDefault(True)
        vbox.adjustSize()
        self._window.adjustSize()

    def show(self):

        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

        while True:
            self._result = self._window.exec_()
            if self._result == QtGui.QDialog.Accepted:
                name = str(self._name.text()).strip()
                if not name:
                    iface.error(_("No name provided!"))
                    continue
                alias = str(self._alias.text()).strip()
                if alias == "*":
                    alias = None
                priority = str(self._priority.value())
                break
            name = alias = priority = None
            break

        self._window.hide()

        return name, alias, priority

class QtSinglePriority(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("Package Priority"))
        self._window.setModal(True)
        
        #self._window.setMinimumSize(600, 400)

        vbox = QtGui.QWidget(self._window)
        QtGui.QVBoxLayout(vbox)
        vbox.layout().setMargin(10)
        vbox.layout().setSpacing(10)
        vbox.show()

        self._vbox = vbox

        self._table = QtGui.QWidget(vbox)
        QtGui.QGridLayout(self._table)
        self._table.layout().setSpacing(10)
        self._table.show()
        vbox.layout().addWidget(self._table)

        bbox = QtGui.QWidget(vbox)
        QtGui.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()
        vbox.layout().addWidget(bbox)

        button = QtGui.QPushButton(_("Close"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("hide()"))
        bbox.layout().addWidget(button)

        self._vbox.adjustSize()
        self._window.adjustSize()

    def show(self, pkg):

        priority = sysconf.get(("package-priorities", pkg.name), {})
        
        table = self._table
        #table.foreach(table.remove)

        label = QtGui.QLabel(_("Package:"), table)
        label.show()
        table.layout().addWidget(label)

        label = QtGui.QLabel("<b>%s</b>" % pkg.name, table)
        label.show()
        table.layout().addWidget(label)

        class AliasCheckBox(QtGui.QCheckBox):
        
            def __init__(self, name, parent):
                QtGui.QSpinBox.__init__(self, name, parent)

            def connect(self, signal, slot, spin, alias):
                QtCore.QObject.connect(self, QtCore.SIGNAL(signal), slot)
                self._spin = spin
                self._alias = alias
            
            def toggled(self, check):
                spin = self._spin
                alias = self._alias
                if check:
                    priority[alias] = int(spin.value())
                    spin.setEnabled(True)
                else:
                    if alias in priority:
                        del priority[alias]
                    spin.setEnabled(False)

        class AliasSpinBox(QtGui.QSpinBox):
        
            def __init__(self, parent):
                QtGui.QSpinBox.__init__(self, parent)
            
            def connect(self, signal, slot, alias):
                QtCore.QObject.connect(self, QtCore.SIGNAL(signal), slot)
                self._alias = alias
            
            def value_changed(self, value):
                alias = spin._alias
                priority[alias] = value

        label = QtGui.QLabel(_("Default priority:"), table)
        label.show()
        table.layout().addWidget(label)

        hbox = QtGui.QWidget(table)
        QtGui.QHBoxLayout(hbox)
        hbox.layout().setSpacing(10)
        hbox.show()
        table.layout().addWidget(hbox)

        radio = QtGui.QRadioButton(_("Channel default"), hbox)
        radio.setChecked(None not in priority)
        radio.show()
        hbox.layout().addWidget(radio)
        
        radio = QtGui.QRadioButton(_("Set to"), hbox)
        radio.setChecked(None in priority)
        radio.show()
        hbox.layout().addWidget(radio)
        spin = QtGui.QSpinBox(hbox)
        spin.setSingleStep(1)
        spin.setRange(-100000,+100000)
        spin.setValue(priority.get(None, 0))
        spin.show()
        table.layout().addWidget(spin)

        label = QtGui.QLabel(_("Channel priority:"), table)
        label.show()
        table.layout().addWidget(label)

        chantable = QtGui.QWidget(table)
        QtGui.QGridLayout(chantable)
        chantable.layout().setSpacing(10)
        chantable.show()
        table.layout().addWidget(chantable)

        pos = 0
        channels = sysconf.get("channels")
        for alias in channels:
            channel = channels[alias]
            if not getChannelInfo(channel.get("type")).kind == "package":
                continue
            name = channel.get("name")
            if not name:
                name = alias
            check = AliasCheckBox(name, chantable)
            check.setChecked(alias in priority)
            check.show()
            chantable.layout().addWidget(check)
            spin = AliasSpinBox(chantable)
            if alias not in priority:
                spin.setEnabled(False)
            spin.setSingleStep(1)
            spin.setRange(-100000,+100000)
            spin.setValue(priority.get(alias, 0))
            spin.connect("valueChanged(int)", spin.value_changed, alias)
            check.connect("toggled(bool)", check.toggled, spin, alias)
            spin.show()
            chantable.layout().addWidget(spin)
            pos += 1
        
        table.adjustSize()
        self._vbox.adjustSize()
        self._window.adjustSize()
        
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        self._window.exec_()
        self._window.hide()

        if not priority:
            sysconf.remove(("package-priorities", pkg.name))
        else:
            sysconf.set(("package-priorities", pkg.name), priority)


# vim:ts=4:sw=4:et

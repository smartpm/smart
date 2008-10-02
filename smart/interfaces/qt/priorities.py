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
from smart.interfaces.qt import getPixmap, centerWindow
from smart.channel import getChannelInfo
from smart import *
import qt

class TextListViewItem(qt.QListViewItem):
    def __init__(self, parent):
        qt.QListViewItem.__init__(self, parent)
        self._text = {}
        self._oldtext = {}

    def setText(self, col, text):
        qt.QListViewItem.setText(self, col, text)
        if col in self._text:
            self._oldtext[col] = self._text[col]
        self._text[col] = text

    def oldtext(self, col):
        return self._oldtext.get(col, None)

class QtPriorities(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(None)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("Priorities"))
        #self._window.setModal(True)

        self._window.setMinimumSize(600, 400)

        layout = qt.QVBoxLayout(self._window)
        layout.setResizeMode(qt.QLayout.FreeResize)

        vbox = qt.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        layout.addWidget(vbox)

        self._treeview = qt.QListView(vbox)
        self._treeview.setAllColumnsShowFocus(True)
        self._treeview.show()

        qt.QObject.connect(self._treeview, qt.SIGNAL("itemRenamed(QListViewItem *, int, const QString &)"), self.itemRenamed)
        qt.QObject.connect(self._treeview, qt.SIGNAL("selectionChanged()"), self.selectionChanged)

        self._treeview.addColumn(_("Package Name"))
        self._treeview.addColumn(_("Channel Alias"))
        self._treeview.addColumn(_("Priority"))

        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = qt.QPushButton(_("New"), bbox)
        button.setEnabled(True)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-add")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.newPriority)
        self._newpriority = button

        button = qt.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-delete")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.delPriority)
        self._delpriority = button

        button = qt.QPushButton(_("Close"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))
        
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
                 item.setRenameEnabled(0, True)
                 item.setRenameEnabled(1, True)
                 item.setRenameEnabled(2, True)

    def show(self):
        self.fill()
        self._window.show()
        centerWindow(self._window)
        self._window.raiseW()
        self._window.exec_loop()
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

    def itemRenamed(self, item, col, newtext):
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

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Package Priority"))
        self._window.setModal(True)

        #self._window.setMinimumSize(600, 400)

        vbox = qt.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        table = qt.QGrid(2, vbox)
        table.setSpacing(10)
        table.show()

        label = qt.QLabel(_("Package Name:"), table)

        self._name = qt.QLineEdit(table)
        self._name.show()

        label = qt.QLabel(_("Channel Alias:"), table)

        self._alias = qt.QLineEdit(table)
        self._alias.setText("*")
        self._alias.show()

        label = qt.QLabel(_("Priority:"), table)

        self._priority = qt.QSpinBox(table)
        self._priority.setSteps(1, 10)
        self._priority.setRange(-100000,+100000)
        self._priority.show()

        sep = qt.QFrame(vbox)
        sep.setFrameShape(qt.QFrame.HLine)
        sep.setFrameShadow(qt.QFrame.Sunken)
        sep.show()

        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = qt.QPushButton(_("Cancel"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("reject()"))

        button = qt.QPushButton(_("OK"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))

        button.setDefault(True)
        vbox.adjustSize()
        self._window.adjustSize()

    def show(self):

        self._window.show()
        self._window.raiseW()
        self._window.setActiveWindow()

        while True:
            self._result = self._window.exec_loop()
            if self._result == qt.QDialog.Accepted:
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

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("Package Priority"))
        self._window.setModal(True)
        
        #self._window.setMinimumSize(600, 400)

        vbox = qt.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        self._vbox = vbox

        self._table = qt.QGrid(2, vbox)
        self._table.setSpacing(10)
        self._table.show()

        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = qt.QPushButton(_("Close"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("hide()"))

        self._vbox.adjustSize()
        self._window.adjustSize()

    def show(self, pkg):

        priority = sysconf.get(("package-priorities", pkg.name), {})
        
        table = self._table
        #table.foreach(table.remove)

        label = qt.QLabel(_("Package:"), table)
        label.show()

        label = qt.QLabel("<b>%s</b>" % pkg.name, table)
        label.show()

        class AliasCheckBox(qt.QCheckBox):
        
            def __init__(self, name, parent):
                qt.QSpinBox.__init__(self, name, parent)

            def connect(self, signal, slot, spin, alias):
                qt.QObject.connect(self, qt.SIGNAL(signal), slot)
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

        class AliasSpinBox(qt.QSpinBox):
        
            def __init__(self, parent):
                qt.QSpinBox.__init__(self, parent)
            
            def connect(self, signal, slot, alias):
                qt.QObject.connect(self, qt.SIGNAL(signal), slot)
                self._alias = alias
            
            def value_changed(self, value):
                alias = spin._alias
                priority[alias] = value

        label = qt.QLabel(_("Default priority:"), table)
        label.show()

        hbox = qt.QHBox(table)
        hbox.setSpacing(10)
        hbox.show()

        radio = qt.QRadioButton(_("Channel default"), hbox)
        radio.setChecked(None not in priority)
        radio.show()
        
        radio = qt.QRadioButton(_("Set to"), hbox)
        radio.setChecked(None in priority)
        radio.show()
        spin = qt.QSpinBox(hbox)
        spin.setSteps(1, 10)
        spin.setRange(-100000,+100000)
        spin.setValue(priority.get(None, 0))
        spin.show()

        label = qt.QLabel(_("Channel priority:"), table)
        label.show()

        chantable = qt.QGrid(2, table)
        chantable.setSpacing(10)
        chantable.show()

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
            spin = AliasSpinBox(chantable)
            if alias not in priority:
                spin.setEnabled(False)
            spin.setSteps(1, 10)
            spin.setRange(-100000,+100000)
            spin.setValue(priority.get(alias, 0))
            spin.connect("valueChanged(int)", spin.value_changed, alias)
            check.connect("toggled(bool)", check.toggled, spin, alias)
            spin.show()
            pos += 1
        
        table.adjustSize()
        self._vbox.adjustSize()
        self._window.adjustSize()
        
        self._window.show()
        self._window.raiseW()
        self._window.setActiveWindow()
        self._window.exec_loop()
        self._window.hide()

        if not priority:
            sysconf.remove(("package-priorities", pkg.name))
        else:
            sysconf.set(("package-priorities", pkg.name), priority)


# vim:ts=4:sw=4:et

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

class TextListViewItem(QtGui.QTreeWidgetItem):
    def __init__(self, parent):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        self._text = {}
        self._oldtext = {}

    def setText(self, col, text):
        QtGui.QTreeWidgetItem.setText(self, col, text)
        if col in self._text:
            self._oldtext[col] = self._text[col]
        self._text[col] = text

    def oldtext(self, col):
        return self._oldtext.get(col, None)

class QtMirrors(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(None)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("Mirrors"))
        self._window.setModal(True)

        self._window.setMinimumSize(600, 400)

        layout = QtGui.QVBoxLayout(self._window)
        #layout.setResizeMode(QtGui.QLayout.FreeResize)

        vbox = QtGui.QWidget(self._window)
        QtGui.QVBoxLayout(vbox)
        vbox.layout().setMargin(10)
        vbox.layout().setSpacing(10)
        vbox.show()

        layout.addWidget(vbox)

        self._treeview = QtGui.QTreeWidget(vbox)
        self._treeview.setHeaderHidden(True)
        self._treeview.show()
        vbox.layout().addWidget(self._treeview)

        #self._treeview.addColumn(_("Mirror"))
        self._treeview.setHeaderLabels([_("Mirror")])
        QtCore.QObject.connect(self._treeview, QtCore.SIGNAL("itemChanged(QTreeWidgetItem *, int)"), self.itemChanged)
        QtCore.QObject.connect(self._treeview, QtCore.SIGNAL("itemSelectionChanged()"), self.selectionChanged)

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
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.newMirror)
        self._newmirror = button
        bbox.layout().addWidget(button)

        button = QtGui.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-delete")))
        button.show()
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self.delMirror)
        self._delmirror = button
        bbox.layout().addWidget(button)

        button = QtGui.QPushButton(_("Close"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        bbox.layout().addWidget(button)
        
        button.setDefault(True)

    def fill(self):
        self._treeview.clear()
        mirrors = sysconf.get("mirrors", {})
        for origin in mirrors:
             parent = TextListViewItem(self._treeview)
             parent.setText(0, origin)
             #parent.setRenameEnabled(0, True)
             for mirror in mirrors[origin]:
                 item = TextListViewItem(parent)
                 item.setText(0, mirror)
                 #item.setRenameEnabled(0, True)
             parent.setExpanded(True)
        
    def show(self):
        self.fill()
        self._window.show()
        centerWindow(self._window)
        self._window.raise_()
        self._window.exec_()
        self._window.hide()

    def newMirror(self):
        item = self._treeview.selectedItems()
        if item:
            item = item[0]
            if item.childCount() == 2:
                item = item.parent()
            origin = str(item.text(0))
        else:
            origin = ""
        origin, mirror = MirrorCreator(self._window).show(origin)
        if origin and mirror:
            sysconf.add(("mirrors", origin), mirror, unique=True)
        self.fill()


    def delMirror(self):
        item = self._treeview.selectedItems()
        if not item:
            return
        item = item[0]
        if item.parent() is None:
            origin = str(item.text(0))
            sysconf.remove(("mirrors", origin))
        else:
            print
            mirror = str(item.text(0))
            origin = str(item.parent().text(0))
            print "%s %s" % (mirror, origin)
            sysconf.remove(("mirrors", origin), mirror)
        self.fill()

    def selectionChanged(self):
        item = self._treeview.selectedItems()
        self._delmirror.setEnabled(bool(item))

    def itemChanged(self, item, col):
        newtext = item.text(col)
        oldtext = item.oldtext(col)
        if not oldtext:
            return
        if not item.parent():
            if sysconf.has(("mirrors", str(newtext))):
                iface.error(_("Origin already exists!"))
            else:
                sysconf.move(("mirrors", str(oldtext)), ("mirrors", str(newtext)))
                
        else:
            origin = item.parent().text(0)
            if sysconf.has(("mirrors", str(origin)), str(newtext)):
                iface.error(_("Mirror already exists!"))
            else:
                sysconf.remove(("mirrors", str(origin)), oldtext)
                sysconf.add(("mirrors", str(origin)), str(newtext), unique=True)


class MirrorCreator(object):

    def __init__(self, parent=None):

        self._window = QtGui.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("New Mirror"))
        self._window.setModal(True)

        #self._window.setMinimumSize(600, 400)

        vbox = QtGui.QWidget(self._window)
        QtGui.QVBoxLayout(vbox)
        vbox.layout().setMargin(10)
        vbox.layout().setSpacing(10)
        vbox.show()

        table = QtGui.QWidget(vbox)
        QtGui.QGridLayout(table)
        table.layout().setSpacing(10)
        table.show()
        vbox.layout().addWidget(table)
        
        label = QtGui.QLabel(_("Origin URL:"), table)
        label.show()
        table.layout().addWidget(label)

        self._origin = QtGui.QLineEdit(table)
        self._origin.setMaxLength(40)
        self._origin.show()
        table.layout().addWidget(self._origin)

        label = QtGui.QLabel(_("Mirror URL:"), table)
        label.show()
        table.layout().addWidget(label)

        self._mirror = QtGui.QLineEdit(table)
        self._mirror.setMaxLength(40)
        self._mirror.show()
        table.layout().addWidget(self._mirror)

        sep = QtGui.QFrame(vbox)
        sep.setFrameStyle(QtGui.QFrame.HLine)
        sep.show()
        vbox.layout().addWidget(sep)

        bbox = QtGui.QWidget(self._window)
        QtGui.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()
        vbox.layout().addWidget(bbox)

        button = QtGui.QPushButton(_("OK"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("accept()"))
        bbox.layout().addWidget(button)

        button = QtGui.QPushButton(_("Cancel"), bbox)
        QtCore.QObject.connect(button, QtCore.SIGNAL("clicked()"), self._window, QtCore.SLOT("reject()"))
        bbox.layout().addWidget(button)
        
        vbox.adjustSize()
        self._window.adjustSize()

    def show(self, origin="", mirror=""):

        self._origin.setText(origin)
        self._mirror.setText(mirror)
        origin = mirror = None

        self._window.show()
        self._window.raise_()

        while True:
            self._result = self._window.exec_()
            if self._result == QtGui.QDialog.Accepted:
                origin = str(self._origin.text()).strip()
                if not origin:
                    iface.error(_("No origin provided!"))
                    continue
                mirror = str(self._mirror.text()).strip()
                if not mirror:
                    iface.error(_("No mirror provided!"))
                    continue
                break
            origin = mirror = None
            break

        self._window.hide()

        return origin, mirror

# vim:ts=4:sw=4:et

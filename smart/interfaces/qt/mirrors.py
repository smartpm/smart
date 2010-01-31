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

class QtMirrors(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(None)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("Mirrors"))
        self._window.setModal(True)

        self._window.setMinimumSize(600, 400)

        layout = qt.QVBoxLayout(self._window)
        layout.setResizeMode(qt.QLayout.FreeResize)

        vbox = qt.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        layout.addWidget(vbox)

        self._treeview = qt.QListView(vbox)
        self._treeview.header().hide()
        self._treeview.show()

        self._treeview.addColumn(_("Mirror"))
        qt.QObject.connect(self._treeview, qt.SIGNAL("itemRenamed(QListViewItem *, int, const QString &)"), self.itemRenamed)
        qt.QObject.connect(self._treeview, qt.SIGNAL("selectionChanged()"), self.selectionChanged)

        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = qt.QPushButton(_("New"), bbox)
        button.setEnabled(True)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-add")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.newMirror)
        self._newmirror = button

        button = qt.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-delete")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.delMirror)
        self._delmirror = button

        button = qt.QPushButton(_("Close"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))
        
        button.setDefault(True)

    def fill(self):
        self._treeview.clear()
        mirrors = sysconf.get("mirrors", {})
        for origin in mirrors:
             parent = TextListViewItem(self._treeview)
             parent.setText(0, origin)
             parent.setRenameEnabled(0, True)
             for mirror in mirrors[origin]:
                 item = TextListViewItem(parent)
                 item.setText(0, mirror)
                 item.setRenameEnabled(0, True)
             parent.setOpen(True)
        
    def show(self):
        self.fill()
        self._window.show()
        centerWindow(self._window)
        self._window.raiseW()
        self._window.exec_loop()
        self._window.hide()

    def newMirror(self):
        item = self._treeview.selectedItem()
        if item:
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
        item = self._treeview.selectedItem()
        if not item:
            return
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
        item = self._treeview.selectedItem()
        self._delmirror.setEnabled(bool(item))

    def itemRenamed(self, item, col, newtext):
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

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Mirror"))
        self._window.setModal(True)

        #self._window.setMinimumSize(600, 400)

        vbox = qt.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        table = qt.QGrid(2, vbox)
        table.setSpacing(10)
        table.show()
        
        label = qt.QLabel(_("Origin URL:"), table)
        label.show()

        self._origin = qt.QLineEdit(table)
        self._origin.setMaxLength(40)
        self._origin.show()

        label = qt.QLabel(_("Mirror URL:"), table)
        label.show()

        self._mirror = qt.QLineEdit(table)
        self._mirror.setMaxLength(40)
        self._mirror.show()

        sep = qt.QFrame(vbox)
        sep.setFrameStyle(qt.QFrame.HLine)
        sep.show()

        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = qt.QPushButton(_("OK"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))

        button = qt.QPushButton(_("Cancel"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("reject()"))
        
        vbox.adjustSize()
        self._window.adjustSize()

    def show(self, origin="", mirror=""):

        self._origin.setText(origin)
        self._mirror.setText(mirror)
        origin = mirror = None

        self._window.show()
        self._window.raiseW()

        while True:
            self._result = self._window.exec_loop()
            if self._result == qt.QDialog.Accepted:
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

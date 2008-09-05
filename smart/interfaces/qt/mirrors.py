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
from smart.interfaces.qt import getPixmap
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
        #self._window.setModal(True)

        #self._window.set_transient_for(parent)
        #self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.setMinimumSize(600, 400)
        #def delete(widget, event):
        #    gtk.main_quit()
        #    return True
        #self._window.connect("delete-event", delete)

        #vbox = gtk.VBox()
        #vbox.set_border_width(10)
        #vbox.set_spacing(10)
        #vbox.show()
        #self._window.add(vbox)
        vbox = qt.QVBox(self._window)
        vbox.setMinimumSize(600, 400) # HACK
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        #sw = gtk.ScrolledWindow()
        #sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        #sw.set_shadow_type(gtk.SHADOW_IN)
        #sw.show()
        #vbox.add(sw)
        sv = qt.QScrollView(vbox)
        sv.show()

        #self._treemodel = gtk.TreeStore(gobject.TYPE_STRING)
        #self._treeview = gtk.TreeView(self._treemodel)
        #self._treeview.set_rules_hint(True)
        #self._treeview.set_headers_visible(False)
        #self._treeview.show()
        #sw.add(self._treeview)
        self._treeview = qt.QListView(sv)
        self._treeview.setMinimumSize(600, 400) # HACK
        self._treeview.header().hide()
        self._treeview.show()

        #renderer = gtk.CellRendererText()
        #renderer.set_property("xpad", 3)
        #renderer.set_property("editable", True)
        #renderer.connect("edited", self.rowEdited)
        #self._treeview.insert_column_with_attributes(-1, _("Mirror"), renderer,
        #                                             text=0)
        self._treeview.addColumn(_("Mirror"))
        qt.QObject.connect(self._treeview, qt.SIGNAL("itemRenamed(QListViewItem *, int, const QString &)"), self.itemRenamed)
        qt.QObject.connect(self._treeview, qt.SIGNAL("selectionChanged()"), self.selectionChanged)

        #bbox = gtk.HButtonBox()
        #bbox.set_spacing(10)
        #bbox.set_layout(gtk.BUTTONBOX_END)
        #bbox.show()
        #vbox.pack_start(bbox, expand=False)
        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        #button = gtk.Button(stock="gtk-new")
        #button.show()
        #button.connect("clicked", lambda x: self.newMirror())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("New"), bbox)
        button.setEnabled(True)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-add")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.newMirror)
        self._newmirror = button

        #button = gtk.Button(stock="gtk-delete")
        #button.show()
        #button.connect("clicked", lambda x: self.delMirror())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-delete")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.delMirror)
        self._delmirror = button

        #button = gtk.Button(stock="gtk-close")
        #button.show()
        #button.connect("clicked", lambda x: gtk.main_quit())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("Close"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))
        
        button.setDefault(True)

    def fill(self):
        #self._treemodel.clear()
        self._treeview.clear()
        mirrors = sysconf.get("mirrors", {})
        for origin in mirrors:
        #    parent = self._treemodel.append(None, (origin,))
        #    for mirror in mirrors[origin]:
        #        iter = self._treemodel.append(parent, (mirror,))
        #self._treeview.expand_all()
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
        self._window.raiseW()
        #gtk.main()
        self._window.exec_loop()
        self._window.hide()

    def newMirror(self):
        #selection = self._treeview.get_selection()
        #model, iter = selection.get_selected()
        item = self._treeview.selectedItem()
        #if iter:
        #    path = model.get_path(iter)
        #    if len(path) == 2:
        #        iter = model.get_iter(path[:1])
        #    origin = model.get_value(iter, 0)
        #else:
        #    origin = ""
        if item:
            if item.childCount() == 2:
                item = item.parent()
            origin = item.text(0)
        else:
            origin = ""
        origin, mirror = MirrorCreator(self._window).show(origin)
        if origin and mirror:
            sysconf.add(("mirrors", str(origin)), str(mirror), unique=True)
        self.fill()


    def delMirror(self):
        #selection = self._treeview.get_selection()
        #model, iter = selection.get_selected()
        item = self._treeview.selectedItem()
        if not item:
            return
        #path = model.get_path(iter)
        #if len(path) == 1:
        #    origin = model.get_value(iter, 0)
        #    sysconf.remove(("mirrors", origin))
        #else:
        #    mirror = model.get_value(iter, 0)
        #    iter = model.get_iter(path[:1])
        #    origin = model.get_value(iter, 0)
        #    sysconf.remove(("mirrors", origin), mirror)
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

    #def rowEdited(self, cell, row, newtext):
    def itemRenamed(self, item, col, newtext):
        #model = self._treemodel
        #iter = model.get_iter_from_string(row)
        #path = model.get_path(iter)
        #oldtext = model.get_value(iter, 0)
        oldtext = item.oldtext(col)
        if not oldtext:
            return
        if not item.parent():
            if sysconf.has(("mirrors", str(newtext))):
                iface.error(_("Origin already exists!"))
            else:
                sysconf.move(("mirrors", str(oldtext)), ("mirrors", str(newtext)))
                #model.set_value(iter, 0, newtext)
                
        else:
            #origin = model.get_value(model.get_iter(path[1:]), 0)
            origin = item.parent().text(0)
            if sysconf.has(("mirrors", str(origin)), str(newtext)):
                iface.error(_("Mirror already exists!"))
            else:
                sysconf.remove(("mirrors", str(origin)), oldtext)
                sysconf.add(("mirrors", str(origin)), str(newtext), unique=True)
                #model.set_value(iter, 0, newtext)


class MirrorCreator(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Mirror"))
        self._window.setModal(True)
        #self._window.set_position(gtk.WIN_POS_CENTER)
        ##self._window.set_geometry_hints(min_width=600, min_height=400)
        #def delete(widget, event):
        #    gtk.main_quit()
        #    return True
        #self._window.connect("delete-event", delete)
        #self._window.setMinimumSize(600, 400)

        #vbox = gtk.VBox()
        #vbox.set_border_width(10)
        #vbox.set_spacing(10)
        #vbox.show()
        #self._window.add(vbox)
        vbox = qt.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        #table = gtk.Table()
        #table.set_row_spacings(10)
        #table.set_col_spacings(10)
        #table.show()
        #vbox.pack_start(table)
        table = qt.QGrid(2, vbox)
        table.setSpacing(10)
        table.show()
        
        #label = gtk.Label(_("Origin URL:"))
        #label.set_alignment(1.0, 0.5)
        #label.show()
        #table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Origin URL:"), table)
        label.show()

        #self._origin = gtk.Entry()
        #self._origin.set_width_chars(40)
        #self._origin.show()
        #table.attach(self._origin, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._origin = qt.QLineEdit(table)
        self._origin.setMaxLength(40)
        self._origin.show()

        #label = gtk.Label(_("Mirror URL:"))
        #label.set_alignment(1.0, 0.5)
        #label.show()
        #table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Mirror URL:"), table)
        label.show()

        #self._mirror = gtk.Entry()
        #self._mirror.set_width_chars(40)
        #self._mirror.show()
        #table.attach(self._mirror, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._mirror = qt.QLineEdit(table)
        self._mirror.setMaxLength(40)
        self._mirror.show()

        #sep = gtk.HSeparator()
        #sep.show()
        #vbox.pack_start(sep, expand=False)
        sep = qt.QFrame(vbox)
        sep.setFrameStyle(qt.QFrame.HLine)
        sep.show()

        #bbox = gtk.HButtonBox()
        #bbox.set_spacing(10)
        #bbox.set_layout(gtk.BUTTONBOX_END)
        #bbox.show()
        #vbox.pack_start(bbox, expand=False)
        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        #self._okbutton = gtk.Button(stock="gtk-ok")
        #self._okbutton.show()
        #def clicked(x):
        #    self._result = True
        #    gtk.main_quit()
        #self._okbutton.connect("clicked", clicked)
        #bbox.pack_start(self._okbutton)
        button = qt.QPushButton(_("OK"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))

        #self._cancelbutton = gtk.Button(stock="gtk-cancel")
        #self._cancelbutton.show()
        #self._cancelbutton.connect("clicked", lambda x: gtk.main_quit())
        #bbox.pack_start(self._cancelbutton)
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

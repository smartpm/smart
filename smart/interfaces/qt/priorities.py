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

        #self._window.set_transient_for(parent)
        #self._window.set_position(gtk.WIN_POS_CENTER)
        #self._window.set_geometry_hints(min_width=600, min_height=400)
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

        #self._treemodel = gtk.ListStore(gobject.TYPE_STRING,
        #                                gobject.TYPE_STRING,
        #                                gobject.TYPE_STRING)
        #self._treeview = gtk.TreeView(self._treemodel)
        #self._treeview.set_rules_hint(True)
        #self._treeview.show()
        #sw.add(self._treeview)
        self._treeview = qt.QListView(sv)
        self._treeview.setMinimumSize(600, 400) # HACK
        self._treeview.setAllColumnsShowFocus(True)
        self._treeview.show()

        qt.QObject.connect(self._treeview, qt.SIGNAL("itemRenamed(QListViewItem *, int, const QString &)"), self.itemRenamed)
        qt.QObject.connect(self._treeview, qt.SIGNAL("selectionChanged()"), self.selectionChanged)

        #self._namerenderer = gtk.CellRendererText()
        #self._namerenderer.set_property("xpad", 3)
        #self._namerenderer.set_property("editable", True)
        #self._namerenderer.connect("edited", self.rowEdited)
        #self._treeview.insert_column_with_attributes(-1, _("Package Name"),
        #                                             self._namerenderer,
        #                                             text=0)
        self._treeview.addColumn(_("Package Name"))

        #self._aliasrenderer = gtk.CellRendererText()
        #self._aliasrenderer.set_property("xpad", 3)
        #self._aliasrenderer.set_property("editable", True)
        #self._aliasrenderer.connect("edited", self.rowEdited)
        #self._treeview.insert_column_with_attributes(-1, _("Channel Alias"),
        #                                             self._aliasrenderer,
        #                                             text=1)
        self._treeview.addColumn(_("Channel Alias"))

        #self._priorityrenderer = gtk.CellRendererText()
        #self._priorityrenderer.set_property("xpad", 3)
        #self._priorityrenderer.set_property("editable", True)
        #self._priorityrenderer.connect("edited", self.rowEdited)
        #self._treeview.insert_column_with_attributes(-1, _("Priority"),
        #                                             self._priorityrenderer,
        #                                             text=2)
        self._treeview.addColumn(_("Priority"))

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
        #button.connect("clicked", lambda x: self.newPriority())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("New"), bbox)
        button.setEnabled(True)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-add")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.newPriority)
        self._newpriority = button

        #button = gtk.Button(stock="gtk-delete")
        #button.show()
        #button.connect("clicked", lambda x: self.delPriority())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-delete")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.delPriority)
        self._delpriority = button

        #button = gtk.Button(stock="gtk-close")
        #button.show()
        #button.connect("clicked", lambda x: gtk.main_quit())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("Close"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))
        
        button.setDefault(True)
        vbox.adjustSize()

    def fill(self):
        #self._treemodel.clear()
        self._treeview.clear()
        priorities = sysconf.get("package-priorities", {})
        prioritieslst = priorities.items()
        prioritieslst.sort()
        for name, pkgpriorities in prioritieslst:
            aliaslst = pkgpriorities.items()
            aliaslst.sort()
            for alias, priority in aliaslst:
        #        self._treemodel.append((name, alias or "*", str(priority)))
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
        self._window.raiseW()
        #gtk.main()
        self._window.exec_loop()
        self._window.hide()

    def newPriority(self):
        name, alias, priority = PriorityCreator(self._window).show()
        if name:
            if sysconf.has(("package-priorities", str(name), str(alias))):
                iface.error(_("Name/alias pair already exists!"))
            else:
                sysconf.set(("package-priorities", str(name), str(alias)), int(priority))
                self.fill()

    def delPriority(self):
        #selection = self._treeview.get_selection()
        #model, iter = selection.get_selected()
        item = self._treeview.selectedItem()
        if item:
            #name = model.get_value(iter, 0)
            #alias = model.get_value(iter, 1)
            name = item.text(0)
            alias = item.text(1)
            if alias == "*":
                alias = None
            sysconf.remove(("package-priorities", str(name), str(alias)))
        self.fill()

    def selectionChanged(self):
        item = self._treeview.selectedItem()
        self._delpriority.setEnabled(bool(item))

    #def rowEdited(self, cell, row, newtext):
    def itemRenamed(self, item, col, newtext):
        newtext = str(newtext).strip()
        #if cell is self._namerenderer:
        #    col = 0
        #elif cell is self._aliasrenderer:
        #    col = 1
        #    if newtext == "*":
        #        newtext = ""
        #else:
        #    col = 2
        #model = self._treemodel
        #iter = model.get_iter_from_string(row)
        #oldtext = model.get_value(iter, col)
        if col == 1:
            if newtext == "*":
                newtext = ""
        oldtext = item.oldtext(col)
        if newtext != oldtext:
            if col == 0:
                #alias = model.get_value(iter, 1)
                alias = item.text(0)
                if alias == "*":
                    alias = None
                #priority = model.get_value(iter, 2)
                priority = item.text(2)
                if not newtext:
                    pass
                elif sysconf.has(("package-priorities", str(newtext), str(alias))):
                    iface.error(_("Name/alias pair already exists!"))
                else:
                    sysconf.set(("package-priorities", str(newtext), str(alias)),
                                int(priority))
                    sysconf.remove(("package-priorities", str(oldtext), str(alias)))
                    #model.set_value(iter, col, newtext)
            elif col == 1:
                #name = model.get_value(iter, 0)
                #priority = model.get_value(iter, 2)
                name = item.text(0)
                priority = item.text(2)
                if sysconf.has(("package-priorities", str(name), str(newtext))):
                    iface.error(_("Name/alias pair already exists!"))
                else:
                    sysconf.move(("package-priorities", str(name), str(oldtext)),
                                 ("package-priorities", str(name), str(newtext)))
                    #model.set_value(iter, col, newtext or "*")
            elif col == 2:
                if newtext:
                    #name = model.get_value(iter, 0)
                    #alias = model.get_value(iter, 1)
                    name = item.text(0)
                    alias = item.text(1)
                    if alias == "*":
                        alias = None
                    try:
                        sysconf.set(("package-priorities", str(name), str(alias)),
                                    int(newtext))
                    except ValueError:
                        item.setText(col, oldtext)
                        iface.error(_("Invalid priority!"))
                    #else:
                    #    model.set_value(iter, col, newtext)

class PriorityCreator(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Package Priority"))
        #self._window.setModal(True)

        #self._window.set_position(gtk.WIN_POS_CENTER)
        ##self._window.set_geometry_hints(min_width=600, min_height=400)
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
        
        #label = gtk.Label(_("Package Name:"))
        #label.set_alignment(1.0, 0.5)
        #label.show()
        #table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Package Name:"), table)

        #self._name = gtk.Entry()
        #self._name.show()
        #table.attach(self._name, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._name = qt.QLineEdit(table)
        self._name.show()

        #label = gtk.Label(_("Channel Alias:"))
        #label.set_alignment(1.0, 0.0)
        #label.show()
        #table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Channel Alias:"), table)

        #self._alias = gtk.Entry()
        ##self._alias.set_text("*")
        #self._alias.show()
        #table.attach(self._alias, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._alias = qt.QLineEdit(table)
        self._alias.setText("*")
        self._alias.show()

        #label = gtk.Label(_("Priority:"))
        #label.set_alignment(1.0, 0.0)
        #label.show()
        #table.attach(label, 0, 1, 2, 3, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Priority:"), table)

        #self._priority = gtk.SpinButton()
        #self._priority.set_width_chars(8)
        #self._priority.set_increments(1, 10)
        #self._priority.set_numeric(True)
        #self._priority.set_range(-100000,+100000)
        #self._priority.show()
        #align = gtk.Alignment(0.0, 0.5)
        #align.show()
        #align.add(self._priority)
        #table.attach(align, 1, 2, 2, 3, gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._priority = qt.QSpinBox(table)
        self._priority.setSteps(1, 10)
        self._priority.setRange(-100000,+100000)
        self._priority.show()

        #sep = gtk.HSeparator()
        #sep.show()
        #vbox.pack_start(sep, expand=False)
        sep = qt.QFrame(vbox)
        sep.setFrameShape(qt.QFrame.HLine)
        sep.setFrameShadow(qt.QFrame.Sunken)
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

        #button = gtk.Button(stock="gtk-cancel")
        #button.show()
        #button.connect("clicked", lambda x: gtk.main_quit())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("Cancel"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("reject()"))

        #button = gtk.Button(stock="gtk-ok")
        #button.show()
        #def clicked(x):
        #    self._result = True
        #    gtk.main_quit()
        #button.connect("clicked", clicked)
        #bbox.pack_start(button)
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
            #gtk.main()
            self._result = self._window.exec_loop()
            if self._result == qt.QDialog.Accepted:
                name = str(self._name.text()).strip()
                if not name:
                    iface.error(_("No name provided!"))
                    continue
                alias = str(self._alias.text()).strip()
                if alias == "*":
                    alias = None
                priority = self._priority.value()
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
        #self._window.setModal(True)
        
        #self._window.set_transient_for(parent)
        #self._window.set_position(gtk.WIN_POS_CENTER)
        #self._window.set_geometry_hints(min_width=600, min_height=400)
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
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        #self._table = gtk.Table()
        #self._table.set_row_spacings(10)
        #self._table.set_col_spacings(10)
        #self._table.show()
        #vbox.pack_start(self._table)
        self._table = qt.QGrid(2, vbox)
        self._table.setSpacing(10)
        self._table.show()

        #bbox = gtk.HButtonBox()
        #bbox.set_spacing(10)
        #bbox.set_layout(gtk.BUTTONBOX_END)
        #bbox.show()
        #vbox.pack_start(bbox, expand=False)
        bbox = qt.QHBox(vbox)
        bbox.setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        #button = gtk.Button(stock="gtk-close")
        #button.show()
        #button.connect("clicked", lambda x: gtk.main_quit())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("Close"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("hide()"))

        vbox.adjustSize()
        self._window.adjustSize()

    def show(self, pkg):

        priority = sysconf.get(("package-priorities", pkg.name), {})
        
        table = self._table
        #table.foreach(table.remove)

        #label = gtk.Label(_("Package:"))
        #label.set_alignment(1.0, 0.5)
        #label.show()
        #table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Package:"), table)
        label.show()

        #label = gtk.Label()
        #label.set_markup("<b>%s</b>" % pkg.name)
        #label.set_alignment(0.0, 0.5)
        #label.show()
        #table.attach(label, 1, 2, 0, 1, gtk.FILL, gtk.FILL)
        label = qt.QLabel("<b>%s</b>" % pkg.name, table)
        label.show()

        def toggled(check, spin, alias):
            if check.get_active():
                priority[alias] = int(spin.get_value())
                spin.set_sensitive(True)
            else:
                if alias in priority:
                    del priority[alias]
                spin.set_sensitive(False)

        def value_changed(spin, alias):
            priority[alias] = int(spin.get_value())

        #label = gtk.Label(_("Default priority:"))
        #label.set_alignment(1.0, 0.5)
        #label.show()
        #table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Default priority:"), table)
        label.show()

        #hbox = gtk.HBox()
        #hbox.set_spacing(10)
        #hbox.show()
        #table.attach(hbox, 1, 2, 1, 2, gtk.FILL, gtk.FILL)
        hbox = qt.QHBox(table)
        hbox.setSpacing(10)
        hbox.show()

        #radio = gtk.RadioButton(None, _("Channel default"))
        #radio.set_active(None not in priority)
        #radio.show()
        #hbox.pack_start(radio, expand=False)
        radio = qt.QRadioButton(_("Channel default"), hbox)
        radio.setEnabled(None not in priority)
        radio.show()
        
        #radio = gtk.RadioButton(radio, _("Set to"))
        #radio.set_active(None in priority)
        #radio.show()
        #hbox.pack_start(radio, expand=False)
        radio = qt.QRadioButton(_("Set to"), hbox)
        radio.setEnabled(None in priority)
        radio.show()
        #spin = gtk.SpinButton()
        #if None not in priority:
        #    spin.set_sensitive(False)
        #spin.set_increments(1, 10)
        #spin.set_numeric(True)
        #spin.set_range(-100000,+100000)
        #spin.set_value(priority.get(None, 0))
        #spin.connect("value-changed", value_changed, None)
        #radio.connect("toggled", toggled, spin, None)
        #spin.show()
        #hbox.pack_start(spin, expand=False)
        spin = qt.QSpinBox(hbox)
        spin.setSteps(1, 10)
        spin.setRange(-100000,+100000)
        spin.setValue(priority.get(None, 0))
        spin.show()

        #label = gtk.Label(_("Channel priority:"))
        #label.set_alignment(1.0, 0.0)
        #label.show()
        #table.attach(label, 0, 1, 2, 3, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Channel priority:"), table)
        label.show()

        #chantable = gtk.Table()
        #chantable.set_row_spacings(10)
        #chantable.set_col_spacings(10)
        #chantable.show()
        #table.attach(chantable, 1, 2, 2, 3, gtk.FILL, gtk.FILL)
        chantable = qt.QGrid(1, vbox)
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
            #check = gtk.CheckButton(name)
            #check.set_active(alias in priority)
            #check.show()
            #chantable.attach(check, 0, 1, pos, pos+1, gtk.FILL, gtk.FILL)
            check = qt.QCheckButton(name, chantable)
            check.setChecked(alias in priority)
            check.show()
            #spin = gtk.SpinButton()
            #if alias not in priority:
            #    spin.set_sensitive(False)
            #spin.set_increments(1, 10)
            #spin.set_numeric(True)
            #spin.set_range(-100000,+100000)
            #spin.set_value(int(priority.get(alias, 0)))
            #spin.connect("value_changed", value_changed, alias)
            #check.connect("toggled", toggled, spin, alias)
            #spin.show()
            #chantable.attach(spin, 1, 2, pos, pos+1, gtk.FILL, gtk.FILL)
            spin = qt.QSpinBox(table)
            if alias not in priority:
                spin.setEnabled(False)
            spin.setSteps(1, 10)
            spin.setRange(-100000,+100000)
            spin.setValue(priority.get(alias, 0))
            spin.show()
            pos += 1
        
        self._window.show()
        #gtk.main()
        self._window.exec_loop()
        self._window.hide()

        if not priority:
            sysconf.remove(("package-priorities", pkg.name))
        else:
            sysconf.set(("package-priorities", pkg.name), priority)


# vim:ts=4:sw=4:et

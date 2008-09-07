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
from smart.util.strtools import strToBool
from smart.const import NEVER
from smart.channel import *
from smart import *
import qt
import textwrap
import os

class RadioAction(qt.QAction):

    def __init__(self, radio, name, label=None):
        qt.QAction.__init__(self, radio, name)
        self._radio = radio
    
    def connect(self, object, field, userdata):
        self._object = object
        self._field = field
        self._userdata = userdata
        signal = "stateChanged(int)"
        qt.QObject.connect(self._radio, qt.SIGNAL(signal), self.slot)
    
    def slot(self, state):
        if state == qt.QButton.On:
            setattr(self._object, self._field, self._userdata)
         
class QtChannels(object):

    def __init__(self, parent=None):

        self._changed = False

        self._window = qt.QDialog(None)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("Channels"))
        self._window.setModal(True)

        #self._window.set_transient_for(parent)
        #self._window.set_position(gtk.WIN_POS_CENTER)
        #self._window.set_geometry_hints(min_width=600, min_height=400)
        #def delete(widget, event):
        #    gtk.main_quit()
        #    return True
        #self._window.connect("delete-event", delete)
        self._window.setMinimumSize(600, 400)

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
        sv.setFrameStyle(qt.QFrame.StyledPanel | qt.QFrame.Sunken)
        sv.show()

        #self._treemodel = gtk.ListStore(gobject.TYPE_INT,
        #                                gobject.TYPE_STRING,
        #                                gobject.TYPE_STRING,
        #                                gobject.TYPE_STRING,
        #                                gobject.TYPE_INT);
        #self._treeview = gtk.TreeView(self._treemodel)
        #self._treeview.set_rules_hint(True)
        #self._treeview.show()
        #sw.add(self._treeview)
        self._treeview = qt.QListView(sv)
        self._treeview.setMinimumSize(600, 400) # HACK
        self._treeview.setAllColumnsShowFocus(True)
        self._treeview.setSelectionMode(qt.QListView.Single)
        self._treeview.show()

        #renderer = gtk.CellRendererToggle()
        #renderer.set_property("xpad", 4)
        #renderer.set_active(False)
        #def toggled(cell, path):
        #    model = self._treemodel
        #    iter = model.get_iter(path)
        #    model.set(iter, 0, not bool(model.get_value(iter, 0)))
        #renderer.connect("toggled", toggled)
        #self._treeview.insert_column_with_attributes(-1, "", renderer,
        #                                             active=0)
        qt.QObject.connect(self._treeview, qt.SIGNAL("selectionChanged()"), self.selectionChanged)
        qt.QObject.connect(self._treeview, qt.SIGNAL("doubleClicked(QListViewItem *, const QPoint &, int)"), self.doubleClicked)

        #renderer = gtk.CellRendererText()
        #renderer.set_property("xpad", 4)
        #self._treeview.insert_column_with_attributes(-1, _("Pri"), renderer,
        #                                             text=4)
        #self._treeview.insert_column_with_attributes(-1, _("Alias"), renderer,
        #                                             text=1)
        #self._treeview.insert_column_with_attributes(-1, _("Type"), renderer,
        #                                             text=2)
        #self._treeview.insert_column_with_attributes(-1, _("Name"), renderer,
        #                                             text=3)
        self._treeview.addColumn(_("Alias"))
        self._treeview.addColumn(_("Type"))
        self._treeview.addColumn(_("Name"))
        self._treeview.addColumn(_("Pri"))
        
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
        #button.connect("clicked", lambda x: self.newChannel())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("New"), bbox)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-add")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.newChannel)
        self._newchannel = button

        #button = gtk.Button(stock="gtk-delete")
        #button.show()
        #def clicked(x):
        #    selection = self._treeview.get_selection()
        #    model, iter = selection.get_selected()
        #    if not iter:
        #        return
        #    alias = model.get_value(iter, 1)
        #    self.delChannel(alias)
        #button.connect("clicked", clicked)
        #bbox.pack_start(button)
        button = qt.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-delete")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.delChannel)
        self._delchannel = button

        #button = gtk.Button(stock="gtk-properties")
        #button.show()
        #def clicked(x):
        #   selection = self._treeview.get_selection()
        #    model, iter = selection.get_selected()
        #    if not iter:
        #        return
        #    alias = model.get_value(iter, 1)
        #    self.editChannel(alias)
        #button.connect("clicked", clicked)
        #bbox.pack_start(button)
        button = qt.QPushButton(_("Edit"), bbox)
        button.setEnabled(False)
        button.setIconSet(qt.QIconSet(getPixmap("crystal-edit")))
        button.show()
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self.editChannel)
        self._editchannel = button

        #button = gtk.Button(stock="gtk-close")
        #button.show()
        #button.connect("clicked", lambda x: gtk.main_quit())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("Close"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))

        button.setDefault(True)
        vbox.adjustSize()

    def fill(self):
        self._treeview.clear()
        channels = sysconf.get("channels", {})
        aliases = channels.keys()
        aliases.sort()
        for alias in aliases:
            channel = channels[alias]
            #self._treemodel.append((not strToBool(channel.get("disabled")),
            #                        alias,
            #                        channel.get("type", ""),
            #                        channel.get("name", ""),
            #                        int(channel.get("priority", "") or 0),
#))
            item = qt.QCheckListItem(self._treeview, alias, qt.QCheckListItem.CheckBoxController)
            item.setOn(not strToBool(channel.get("disabled")))
            item.setText(0, alias)
            item.setText(1, channel.get("type", ""))
            item.setText(2, channel.get("name", ""))
            item.setText(3, channel.get("priority", "0"))

    def enableDisable(self):
        iter = qt.QListViewItemIterator(self._treeview)
        while iter.current():
            item = iter.current()
            disabled = strToBool(sysconf.get(("channels", item.text(0), "disabled")))
            if item.isOn():
                if disabled:
                    sysconf.remove(("channels", item.text(0), "disabled"))
                    self._changed = True
            else:
                if not disabled:
                    sysconf.set(("channels", item.text(0), "disabled"), True)
                    self._changed = True
            iter += 1
            
    def show(self):
        self.fill()
        self._window.show()
        self._window.raiseW()
        self._window.setActiveWindow()
        self._window.exec_loop()
        self._window.hide()
        self.enableDisable()
        return self._changed

    def newChannel(self):
        self.enableDisable()

        method = MethodSelector(self._window).show()
        if not method:
            return

        editor = ChannelEditor(self._window)

        path = None
        removable = []

        if method == "manual":

            type = TypeSelector(self._window).show()
            if not type:
                return

            newchannel = {"type": type}
            if editor.show(None, newchannel, editalias=True):
                alias = newchannel["alias"]
                del newchannel["alias"]
                sysconf.set(("channels", alias),
                            parseChannelData(newchannel))
                self._changed = True
                if newchannel.get("removable"):
                    removable.append(alias)

        elif method in ("descriptionpath", "descriptionurl"):

            if method == "descriptionpath":
                #if gtk.pygtk_version > (2,4,0):
                #    dia = gtk.FileChooserDialog(
                #        action=gtk.FILE_CHOOSER_ACTION_OPEN,
                #        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                #                 gtk.STOCK_OK, gtk.RESPONSE_OK))
                #                 
                #else:
                #    dia = gtk.FileSelection(_("Select Channel Description"))
                #    dia.hide_fileop_buttons()
                #response = dia.run()
                #filename = dia.get_filename()
                #dia.destroy()
                #if response != gtk.RESPONSE_OK:
                #    return
                filename = qt.QFileDialog.getOpenFileName("", "",
                     self._window, "", _("Select Channel Description"))
                if not filename:
                    return
                if not os.path.isfile(filename):
                    iface.error(_("File not found: %s") % filename)
                    return
                file = open(filename)
                data = file.read()
                file.close()
            elif method == "descriptionurl":
                url = iface.askInput(_("Description URL"))
                if not url:
                    return
                ctrl = iface.getControl()
                succ, fail = ctrl.downloadURLs([url], _("channel description"))
                if fail:
                    iface.error(_("Unable to fetch channel description: %s")
                                % fail[url])
                    return
                file = open(succ[url])
                data = file.read()
                file.close()
                if succ[url].startswith(sysconf.get("data-dir")):
                    os.unlink(succ[url])
            
            newchannels = parseChannelsDescription(data)
            for alias in newchannels:
                newchannel = newchannels[alias]
                if editor.show(alias, newchannel, editalias=True):
                    alias = newchannel["alias"]
                    del newchannel["alias"]
                    sysconf.set(("channels", alias),
                                parseChannelData(newchannel))
                    self._changed = True
                    if newchannel.get("removable"):
                        removable.append(alias)

        elif method in ("detectmedia", "detectpath"):

            if method == "detectmedia":
                path = MountPointSelector().show()
                if not path:
                    return
            elif method == "detectpath":
                #if gtk.pygtk_version > (2,4,0):
                #    dia = gtk.FileChooserDialog(
                #        action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                #        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                #                 gtk.STOCK_OK, gtk.RESPONSE_OK))
                #                 
                #else:
                #    dia = gtk.FileSelection(_("Select Path"))
                #    dia.hide_fileop_buttons()
                #response = dia.run()
                #path = dia.get_filename()
                #dia.destroy()
                #if response != gtk.RESPONSE_OK:
                #    return
                path = qt.QFileDialog.getExistingDirectory("",
                     self._window, "", _("Select Path"), True)
                if not path:
                    return
                if not os.path.isdir(path):
                    iface.error(_("Directory not found: %s") % path)
                    return

            sysconf.set("default-localmedia", path, soft=True)

            foundchannel = False
            for newchannel in detectLocalChannels(path):
                foundchannel = True
                if editor.show(newchannel.get("alias"), newchannel,
                               editalias=True):
                    alias = newchannel["alias"]
                    del newchannel["alias"]
                    sysconf.set(("channels", alias),
                                parseChannelData(newchannel))
                    self._changed = True
                    if newchannel.get("removable"):
                        removable.append(alias)
            
            if not foundchannel:
                iface.error(_("No channels detected!"))
                return

        if removable:
            ctrl = iface.getControl()
            ctrl.rebuildSysConfChannels()
            channels = [x for x in ctrl.getChannels()
                        if x.getAlias() in removable]
            iface.updateChannels(channels=channels)

        if path:
            sysconf.remove("default-localmedia", soft=True)

        if self._changed:
            self.fill()

    def editChannel(self):
        item = self._treeview.selectedItem()
        if item:
            alias = str(item.text(0))
        else:
            return
        self.enableDisable()
        channel = sysconf.get(("channels", alias), {})
        editor = ChannelEditor(self._window)
        if editor.show(alias, channel):
            sysconf.set(("channels", alias),
                        parseChannelData(channel))
            self._changed = True
            self.fill()

    def delChannel(self):
        item = self._treeview.selectedItem()
        if item:
            alias = item.text(0)
        else:
            return
        if sysconf.remove(("channels", alias)):
            self._changed = True
            self.fill()

    def selectionChanged(self):
        item = self._treeview.selectedItem()
        if item:
            self._editchannel.setEnabled(True)
            self._delchannel.setEnabled(True)
        else:
            self._editchannel.setEnabled(False)
            self._delchannel.setEnabled(False)

    def doubleClicked(self, item, pnt, c):
        self.editChannel()

class QtChannelSelector(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("Select Channels"))
        self._window.setModal(True)

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

        #self._scrollwin = gtk.ScrolledWindow()
        #self._scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        #self._scrollwin.set_shadow_type(gtk.SHADOW_IN)
        #self._scrollwin.show()
        #vbox.add(self._scrollwin)
        self._scrollview = qt.QScrollView(vbox)
        self._scrollview.show()

        #self._treemodel = gtk.ListStore(gobject.TYPE_INT,
        #                                gobject.TYPE_STRING,
        #                                gobject.TYPE_STRING,
        #                                gobject.TYPE_STRING)
        #self._treeview = gtk.TreeView(self._treemodel)
        #self._treeview.set_rules_hint(True)
        #self._treeview.show()
        #self._scrollwin.add(self._treeview)
        self._treeview = qt.QListView(self._scrollview)
        self._treeview.setMinimumSize(400,200)
        self._treeview.show()

        #renderer = gtk.CellRendererToggle()
        #renderer.set_property("xpad", 3)
        #renderer.set_active(False)
        #def toggled(cell, path):
        #    model = self._treemodel
        #    iter = model.get_iter(path)
        #    model.set(iter, 0, not bool(model.get_value(iter, 0)))
        #renderer.connect("toggled", toggled)
        #self._treeview.insert_column_with_attributes(-1, "", renderer,
        #                                             active=0)

        #renderer = gtk.CellRendererText()
        #renderer.set_property("xpad", 3)
        #self._treeview.insert_column_with_attributes(-1, _("Alias"), renderer,
        #                                             text=1)
        #self._treeview.insert_column_with_attributes(-1, _("Type"), renderer,
        #                                             text=2)
        #self._treeview.insert_column_with_attributes(-1, _("Name"), renderer,
        #                                             text=3)
        self._treeview.addColumn(_("Alias"))
        self._treeview.addColumn(_("Type"))
        self._treeview.addColumn(_("Name"))

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
        self._treeview.adjustSize()
        self._window.adjustSize()

    def fill(self):
        #self._treemodel.clear()
        self._treeview.clear()
        channels = sysconf.get("channels", {})
        aliases = channels.keys()
        aliases.sort()
        for alias in aliases:
            channel = channels[alias]
            if not channel.get("disabled"):
                #self._treemodel.append((False, alias,
                #                        channel.get("type", ""),
                #                        channel.get("name", "")))
                item = qt.QCheckListItem(self._treeview, alias)
                item.setOn(False)
                item.setText(0, alias)
                item.setText(1, channel.get("type", ""))
                item.setText(2, channel.get("name", ""))

    def show(self):
        self.fill()
        self._result = False
        self._window.show()
        self._result = self._window.exec_loop()
        self._window.hide()

        result = []
        if self._result == qt.QDialog.Accepted:
            #for row in self._treemodel:
            #    if row[0]:
            #        result.append(row[1])
            iter = qt.QListViewItemIterator(self._treeview)
            while iter.current():
                item = iter.current()
                if item.text(0):
                      result.append(item.text(1)) 
                iter += 1

        return result

class ChannelEditor(object):

    def __init__(self, parent=None):

        self._fields = {}
        self._fieldn = 0

        #self._tooltips = gtk.Tooltips()

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("Edit Channel"))
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
        vbox.setMinimumSize(200,100) # HACK
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()
        self._vbox = vbox

        #self._table = gtk.Table()
        #self._table.set_row_spacings(10)
        #self._table.set_col_spacings(10)
        #self._table.show()
        #vbox.pack_start(self._table)
        self._table = qt.QGrid(2, vbox)
        self._table.setSpacing(10)
        self._table.show()

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

    def addField(self, key, label, value, ftype,
                 editable=True, tip=None, needed=False):

        if ftype is bool:
            #widget = gtk.CheckButton(label)
            #widget.set_active(value)
            #align = gtk.Alignment(0.0, 0.5)
            #align.add(widget)
            #child = align
            spacer = qt.QWidget(self._table)
            spacer.show()
            widget = qt.QCheckBox(label, self._table)
            widget.setChecked(value)
        else:
            #_label = gtk.Label("%s:" % label)
            #_label.set_alignment(1.0, 0.5)
            #_label.show()
            _label = qt.QLabel("%s:" % label, self._table)
            _label.show()
            #self._table.attach(_label, 0, 1, self._fieldn, self._fieldn+1,
            #                   gtk.FILL, gtk.FILL)
            if tip:
                #self._tooltips.set_tip(_label, tip)
                qt.QToolTip.add(_label, tip)
            if ftype is int:
                #widget = gtk.SpinButton()
                #widget.set_increments(1, 10)
                #widget.set_numeric(True)
                #widget.set_range(-100000,+100000)
                #widget.set_value(value)
                #widget.set_width_chars(8)
                #align = gtk.Alignment(0.0, 0.5, 0.0, 0.0)
                #align.add(widget)
                #align.show()
                #child = align
                widget = qt.QSpinBox(self._table)
                widget.setSteps(1, 10)
                widget.setRange(-100000,+100000)
                widget.setValue(value)
            elif ftype is str:
                #widget = gtk.Entry()
                #widget.set_text(value)
                widget = qt.QLineEdit(self._table)
                widget.setText(value)
                if key in ("alias", "type"):
                    #widget.set_width_chars(20)
                    widget.setMaxLength(20)
                    #align = gtk.Alignment(0.0, 0.5, 0.0, 0.0)
                    #align.add(widget)
                    #align.show()
                    #child = align
                else:
                    #widget.set_width_chars(40)
                    widget.setMaxLength(40)
            else:
                raise Error, _("Don't know how to handle %s fields") % ftype

        #child.show_all()
        widget.show()

        #widget.set_property("sensitive", bool(editable))
        widget.setEnabled(bool(editable))
        if tip:
            #self._tooltips.set_tip(widget, tip)
            qt.QToolTip.add(widget, tip)

        #self._table.attach(child, 1, 2, self._fieldn, self._fieldn+1,
        #                   gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._fields[key] = widget
        self._fieldn += 1

    def show(self, alias, oldchannel, editalias=False):
        # reset the dialog fields
        #self._table.foreach(self._table.remove)
        for item in self._table.children():
            if isinstance(item, qt.QWidget): 
                self._table.removeChild(item)
                del item
        
        self._fieldn = 0

        if len(oldchannel) > 1:
            # This won't be needed once old format channels
            # are converted.
            channel = parseChannelData(oldchannel)
        else:
            channel = oldchannel.copy()

        info = getChannelInfo(channel.get("type"))

        for key, label, ftype, default, descr in info.fields:
            if key == "type" or (key == "alias" and not editalias):
                editable = False
            else:
                editable = True
            if key == "alias":
                value = alias
            else:
                value = channel.get(key, default)
            if value is None:
                value = ftype()
            tip = "\n".join(textwrap.wrap(text=descr, width=40))
            self.addField(key, label, value, ftype, editable, tip)

        self._vbox.adjustSize()
        self._window.adjustSize()

        self._window.show()
        self._window.raiseW()

        while True:
            #gtk.main()
            self._result = self._window.exec_loop()
            if self._result == qt.QDialog.Accepted:
                newchannel = {}
                for key, label, ftype, default, descr in info.fields:
                    widget = self._fields[key]
                    if ftype == str:
                        #newchannel[key] = widget.get_text().strip()
                        newchannel[key] = str(widget.text()).strip()
                    elif ftype == int:
                        #newchannel[key] = int(widget.get_text())
                        newchannel[key] = int(widget.text())
                    elif ftype == bool:
                        #newchannel[key] = widget.get_active()
                        newchannel[key] = widget.isChecked()
                    else:
                        raise Error, _("Don't know how to handle %s fields") %\
                                     ftype
                try:
                    if editalias:
                        value = newchannel["alias"]
                        if not value:
                            raise Error, _("Invalid alias!")
                        if (value != alias and 
                            sysconf.has(("channels", value))):
                            raise Error, _("Alias already in use!")
                        if not alias:
                            alias = value
                    createChannel(alias, newchannel)
                except Error, e:
                    iface.error(unicode(e))
                    continue
                else:
                    oldchannel.clear()
                    oldchannel.update(newchannel)
            break

        self._window.hide()

        return self._result

class TypeSelector(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Channel"))
        self._window.setModal(True)
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
        self._vbox = vbox

        #table = gtk.Table()
        #table.set_row_spacings(10)
        #table.set_col_spacings(10)
        #table.show()
        #vbox.pack_start(table)
        table = qt.QGrid(2, vbox)
        table.setSpacing(10)
        table.show()
        self._table = table
        
        #label = gtk.Label(_("Type:"))
        #label.set_alignment(1.0, 0.0)
        #label.show()
        #table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Type:"), table)

        #self._typevbox = gtk.VBox()
        #self._typevbox.set_spacing(10)
        #self._typevbox.show()
        #table.attach(self._typevbox, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._typevbox = qt.QVButtonGroup(table)
        self._typevbox.setFrameStyle(qt.QFrame.NoFrame)
        self._typevbox.show()

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

        #self._ok = button = gtk.Button(stock="gtk-ok")
        #button.show()
        #def clicked(x):
        #    self._result = True
        #    gtk.main_quit()
        #button.connect("clicked", clicked)
        #bbox.pack_start(button)
        button = qt.QPushButton(_("OK"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))

        self._ok = button
        self._ok.setEnabled(False)

    def show(self):
        #self._typevbox.foreach(self._typevbox.remove)
        for item in self._typevbox.children():
            if isinstance(item, qt.QWidget): 
                self._typevbox.removeChild(item)
                del item
        self._type = None

        #radio = None
        #def type_toggled(button, type):
        #    if button.get_active():
        #        self._type = type
        infos = [(info.name, type) for type, info in
                 getAllChannelInfos().items()]
        infos.sort()
        for name, type in infos:
            if not self._type:
                self._type = type
            #radio = gtk.RadioButton(radio, name)
            #radio.connect("activate", lambda x: self._ok.activate())
            #radio.connect("toggled", type_toggled, type)
            #radio.show()
            #self._typevbox.pack_start(radio)
            radio = qt.QRadioButton(name, self._typevbox, type)
            qt.QObject.connect(radio, qt.SIGNAL("clicked()"), self.ok)
            act = RadioAction(radio, type, name)
            act.connect(self, "_type", type)
            radio.show()

        self._typevbox.adjustSize()
        self._table.adjustSize()
        self._vbox.adjustSize()
        self._window.adjustSize()

        self._window.show()
        self._window.raiseW()

        type = None
        while True:
            self._result = self._window.exec_loop()
            if self._result == qt.QDialog.Accepted:
                type = self._type
                break
            type = None
            break

        self._window.hide()

        return type

    def ok(self):
        self._ok.setEnabled(True)
        self._ok.setDefault((True))

class MethodSelector(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Channel"))
        self._window.setModal(True)
        #self._window.set_position(gtk.WIN_POS_CENTER)
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
        table = qt.QGrid(1, vbox)
        table.setSpacing(10)
        table.show()
        
        #label = gtk.Label(_("Method:"))
        #label.set_alignment(1.0, 0.0)
        #label.show()
        #table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Method:"), table)

        #methodvbox = gtk.VBox()
        #methodvbox.set_spacing(10)
        #methodvbox.show()
        #table.attach(methodvbox, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, gtk.FILL)
        methodvbox = qt.QVButtonGroup(table)
        methodvbox.show()

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

        #ok = button = gtk.Button(stock="gtk-ok")
        #button.show()
        #def clicked(x):
        #    self._result = True
        #    gtk.main_quit()
        #button.connect("clicked", clicked)
        #bbox.pack_start(button)
        button = qt.QPushButton(_("OK"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))

        self._ok = button
        self._ok.setEnabled(False)
        
        #radio = None
        self._method = None
        #def method_toggled(button, method):
        #    if button.get_active():
        #        self._method = method
        for method, descr in [("manual",
                               _("Provide channel information")),
                              ("descriptionpath",
                               _("Read channel description from local path")),
                              ("descriptionurl",
                               _("Read channel description from URL")),
                              ("detectmedia",
                               _("Detect channel in media (CDROM, DVD, etc)")),
                              ("detectpath",
                               _("Detect channel in local path"))]:
            if not self._method:
                self._method = method
            #radio = gtk.RadioButton(radio, descr)
            #radio.connect("activate", lambda x: ok.activate())
            #radio.connect("toggled", method_toggled, method)
            #radio.show()
            #methodvbox.pack_start(radio)
            radio = qt.QRadioButton(descr, methodvbox, method)
            qt.QObject.connect(radio, qt.SIGNAL("clicked()"), self.ok)
            act = RadioAction(radio, method, descr)
            act.connect(self, "_method", method)
            radio.show()
        
        methodvbox.adjustSize()
        vbox.adjustSize()
        self._window.adjustSize()

    def show(self):

        self._window.show()
        self._window.raiseW()

        method = None
        while True:
            #gtk.main()
            self._result = self._window.exec_loop()
            if self._result == qt.QDialog.Accepted:
                method = self._method
                break
            method = None
            break

        self._window.hide()

        return method

    def ok(self):
        self._ok.setEnabled(True)
        self._ok.setDefault((True))

class MountPointSelector(object):

    def __init__(self, parent=None):

        self._window = qt.QDialog(parent)
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("New Channel"))
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
        
        #label = gtk.Label(_("Media path:"))
        #label.set_alignment(1.0, 0.0)
        #label.show()
        #table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL)
        label = qt.QLabel(_("Media path:"), table)

        #self._mpvbox = gtk.VBox()
        #self._mpvbox.set_spacing(10)
        #self._mpvbox.show()
        #table.attach(self._mpvbox, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._mpvbox = qt.QVBox(table)
        self._mpvbox.setSpacing(10)
        self._mpvbox.show()

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

        #self._ok = button = gtk.Button(stock="gtk-ok")
        #button.show()
        #def clicked(x):
        #    self._result = True
        #    gtk.main_quit()
        #button.connect("clicked", clicked)
        #bbox.pack_start(button)
        button = qt.QPushButton(_("OK"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("accept()"))

        #button = gtk.Button(stock="gtk-cancel")
        #button.show()
        #button.connect("clicked", lambda x: gtk.main_quit())
        #bbox.pack_start(button)
        button = qt.QPushButton(_("Cancel"), bbox)
        qt.QObject.connect(button, qt.SIGNAL("clicked()"), self._window, qt.SLOT("reject()"))

    def show(self):
        #self._mpvbox.foreach(self._mpvbox.remove)
        self._mp = None

        #radio = None
        group = qt.QButtonGroup(None, "mp")
        #def mp_toggled(button, mp):
        #    if button.get_active():
        #        self._mp = mp
        n = 0
        for media in iface.getControl().getMediaSet():
            mp = media.getMountPoint()
            if not self._mp:
                self._mp = mp
            #radio = gtk.RadioButton(radio, mp)
            #radio.connect("activate", lambda x: self._ok.activate())
            #radio.connect("toggled", mp_toggled, mp)
            #radio.show()
            #self._mpvbox.pack_start(radio)
            radio = qt.QRadioButton(mp, self._mpvbox)
            group.insert(radio)
            act = RadioAction(radio, mp)
            act.connect(self, "_mp", mp)
            radio.show()
            n += 1

        if n == 0:
            iface.error(_("No local media found!"))
            return None
        elif n == 1:
            return self._mp

        self._window.show()
        self._window.raiseW()

        mp = None
        while True:
            #gtk.main()
            self._result = self._window.exec_loop()
            if self._result == qt.QDialog.Accepted:
                mp = self._mp
                break
            mp = None
            break

        self._window.hide()

        return mp

# vim:ts=4:sw=4:et

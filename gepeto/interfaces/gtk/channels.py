#!/usr/bin/python
from gepeto.util.strtools import strToBool
from gepeto.channel import createChannel
from gepeto import *
import gobject, gtk

TYPES = [
    ("rpm-db", "Local RPM database"),
    ("apt-rpm", "APT-RPM repository")
]

# Fields needed by given types, besides alias, type, name, description
# and priority which are common. Every field is of the form:
# (<field-key>, <label>, <tooltip>)
FIELDS = {
    "rpm-db": [],
    "apt-rpm": [("baseurl", "Base URL",
                 "Base URL of APT-RPM repository,\nwhere base/ is located"),
                ("components", "Components",
                 "Space separated list of components")],
}

class GtkChannels(object):

    def __init__(self):

        self._window = gtk.Window()
        self._window.set_title("Channels")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=600, min_height=400)
        def delete(widget, event):
            gtk.main_quit()
            return True
        self._window.connect("delete-event", delete)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self._window.add(self._vbox)

        self._scrollwin = gtk.ScrolledWindow()
        self._scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self._scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self._scrollwin.show()
        self._vbox.add(self._scrollwin)

        self._treemodel = gtk.ListStore(gobject.TYPE_INT,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING)
        self._treeview = gtk.TreeView(self._treemodel)
        self._treeview.set_rules_hint(True)
        self._treeview.show()
        self._scrollwin.add(self._treeview)

        column = gtk.TreeViewColumn("S")
        renderer = gtk.CellRendererToggle()
        renderer.set_property("xpad", 3)
        renderer.set_active(False)
        def toggled(cell, path):
            model = self._treemodel
            iter = model.get_iter(path)
            model.set(iter, 0, not bool(model.get_value(iter, 0)))
        renderer.connect("toggled", toggled)
        self._treeview.insert_column_with_attributes(-1, "", renderer,
                                                     active=0)

        renderer = gtk.CellRendererText()
        renderer.set_property("xpad", 3)
        self._treeview.insert_column_with_attributes(-1, "Alias", renderer,
                                                     text=1)
        self._treeview.insert_column_with_attributes(-1, "Type", renderer,
                                                     text=2)
        self._treeview.insert_column_with_attributes(-1, "Name", renderer,
                                                     text=3)

        bbox = gtk.HButtonBox()
        bbox.set_spacing(10)
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.show()
        self._vbox.pack_start(bbox, expand=False)

        self._newbutton = gtk.Button(stock="gtk-new")
        self._newbutton.show()
        self._newbutton.connect("clicked", lambda x: self.newChannel())
        bbox.pack_start(self._newbutton)

        self._deletebutton = gtk.Button(stock="gtk-delete")
        self._deletebutton.show()
        def clicked(x):
            selection = self._treeview.get_selection()
            model, iter = selection.get_selected()
            if not iter:
                return
            alias = model.get_value(iter, 1)
            self.delChannel(alias)
        self._deletebutton.connect("clicked", clicked)
        bbox.pack_start(self._deletebutton)

        self._propbutton = gtk.Button(stock="gtk-properties")
        self._propbutton.show()
        def clicked(x):
            selection = self._treeview.get_selection()
            model, iter = selection.get_selected()
            if not iter:
                return
            alias = model.get_value(iter, 1)
            self.editChannel(alias)
        self._propbutton.connect("clicked", clicked)
        bbox.pack_start(self._propbutton)

        self._closebutton = gtk.Button(stock="gtk-close")
        self._closebutton.show()
        self._closebutton.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(self._closebutton)

    def fill(self):
        self._treemodel.clear()
        channels = sysconf.get("channels", setdefault={})
        for alias in channels:
            channel = channels[alias]
            self._treemodel.append((not strToBool(channel.get("disabled")),
                                    alias,
                                    channel.get("type", ""),
                                    channel.get("name", "")))

    def show(self):
        self.fill()
        self._window.show()
        gtk.main()
        self._window.hide()

    def newChannel(self):
        alias, type = ChannelCreator().show()
        if alias and type:
            newchannel = {"type": type}
            if ChannelEditor().show(alias, newchannel):
                channels = sysconf.get("channels", setdefault={})
                channels[alias] = newchannel
                self.fill()

    def editChannel(self, alias):
        channels = sysconf.get("channels", setdefault={})
        channel = channels[alias]
        editor = ChannelEditor()
        if editor.show(alias, channel):
            self.fill()

    def delChannel(self, alias):
        channels = sysconf.get("channels", setdefault={})
        del channels[alias]
        self.fill()

class ChannelEditor(object):

    def __init__(self):

        self._fields = {}
        self._fieldn = 0

        self._tooltips = gtk.Tooltips()

        self._window = gtk.Window()
        self._window.set_title("Edit Channel")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        #self._window.set_geometry_hints(min_width=600, min_height=400)
        def delete(widget, event):
            gtk.main_quit()
            return True
        self._window.connect("delete-event", delete)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self._window.add(self._vbox)

        self._table = gtk.Table()
        self._table.set_row_spacings(10)
        self._table.set_col_spacings(10)
        self._table.show()
        self._vbox.pack_start(self._table)

        sep = gtk.HSeparator()
        sep.show()
        self._vbox.pack_start(sep, expand=False)

        bbox = gtk.HButtonBox()
        bbox.set_spacing(10)
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.show()
        self._vbox.pack_start(bbox, expand=False)

        self._okbutton = gtk.Button(stock="gtk-ok")
        self._okbutton.show()
        def clicked(x):
            self._result = True
            gtk.main_quit()
        self._okbutton.connect("clicked", clicked)
        bbox.pack_start(self._okbutton)

        self._cancelbutton = gtk.Button(stock="gtk-cancel")
        self._cancelbutton.show()
        self._cancelbutton.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(self._cancelbutton)

    def addField(self, key, label, text, editable=True,
                 small=False, tip=None, spin=False):
        label = gtk.Label("%s:" % label)
        label.set_alignment(1.0, 0.5)
        label.show()
        self._table.attach(label, 0, 1, self._fieldn, self._fieldn+1,
                           gtk.FILL, gtk.FILL)
        if spin:
            entry = gtk.SpinButton()
            entry.set_increments(1, 10)
            entry.set_numeric(True)
            entry.set_range(-100000,+100000)
        else:
            entry = gtk.Entry()
        entry.set_property("sensitive", bool(editable))
        entry.set_text(text)
        entry.show()
        if small or spin:
            if spin:
                entry.set_width_chars(8)
            else:
                entry.set_width_chars(20)
            align = gtk.Alignment(0.0, 0.5)
            align.add(entry)
            align.show()
            child = align
        else:
            entry.set_width_chars(40)
            child = entry
        self._table.attach(child, 1, 2, self._fieldn, self._fieldn+1,
                           gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._fields[key] = entry
        self._fieldn += 1
        if tip:
            self._tooltips.set_tip(label, tip)
            self._tooltips.set_tip(entry, tip)

    def show(self, alias, channel):
        self._table.foreach(self._table.remove)

        # Enabled checkbox
        enabled = gtk.CheckButton("Enabled")
        enabled.set_active(not strToBool(channel.get("disabled")))
        enabled.show()
        align = gtk.Alignment(0.0, 0.5)
        align.add(enabled)
        align.show()
        self._table.attach(align, 1, 2, self._fieldn, self._fieldn+1,
                           gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._fieldn += 1

        # Other common fields:
        self.addField("alias", "Alias", alias, editable=False, small=True)
        self.addField("type", "Type", channel.get("type", ""),
                      editable=False, small=True)
        self.addField("priority", "Priority", channel.get("priority", "0"),
                      spin=True)
        self.addField("name", "Name", channel.get("name", ""))
        self.addField("description", "Description",
                      channel.get("description", ""))

        # Specific fields:
        for key, label, tip in FIELDS.get(channel.get("type"), ()):
            self.addField(key, label, channel.get(key, ""), tip=tip)

        self._window.show()

        self._result = False
        while True:
            gtk.main()
            if self._result:
                newchannel = channel.copy()
                if not enabled.get_active():
                    newchannel["disabled"] = "yes"
                elif "disabled" in channel:
                    del newchannel["disabled"]
                for key in self._fields:
                    if key not in ("alias", "type"):
                        entry = self._fields[key]
                        value = entry.get_text().strip()
                        if not value and key in newchannel:
                            del newchannel[key]
                        else:
                            newchannel[key] = value
                try:
                    createChannel(newchannel.get("type"), alias, newchannel)
                except Error, e:
                    self._result = False
                    iface.error(str(e))
                    continue
                else:
                    channel.clear()
                    channel.update(newchannel)
            break

        self._window.hide()

        return self._result

class ChannelCreator(object):

    def __init__(self):

        self._window = gtk.Window()
        self._window.set_title("New Channel")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        #self._window.set_geometry_hints(min_width=600, min_height=400)
        def delete(widget, event):
            gtk.main_quit()
            return True
        self._window.connect("delete-event", delete)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self._window.add(self._vbox)

        table = gtk.Table()
        table.set_row_spacings(10)
        table.set_col_spacings(10)
        table.show()
        self._vbox.pack_start(table)
        
        label = gtk.Label("Alias:")
        label.set_alignment(1.0, 0.5)
        label.show()
        table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL)

        self._alias = gtk.Entry()
        self._alias.show()
        align = gtk.Alignment(0.0, 0.5)
        align.add(self._alias)
        align.show()
        table.attach(align, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL, gtk.FILL)

        label = gtk.Label("Type:")
        label.set_alignment(1.0, 0.0)
        label.show()
        table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL)

        self._typevbox = gtk.VBox()
        self._typevbox.set_spacing(10)
        self._typevbox.show()
        table.attach(self._typevbox, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, gtk.FILL)

        sep = gtk.HSeparator()
        sep.show()
        self._vbox.pack_start(sep, expand=False)

        bbox = gtk.HButtonBox()
        bbox.set_spacing(10)
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.show()
        self._vbox.pack_start(bbox, expand=False)

        self._okbutton = gtk.Button(stock="gtk-ok")
        self._okbutton.show()
        def clicked(x):
            self._result = True
            gtk.main_quit()
        self._okbutton.connect("clicked", clicked)
        bbox.pack_start(self._okbutton)

        self._cancelbutton = gtk.Button(stock="gtk-cancel")
        self._cancelbutton.show()
        self._cancelbutton.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(self._cancelbutton)

    def show(self):
        self._typevbox.foreach(self._typevbox.remove)
        self._type = None

        radio = None
        def type_toggled(button, type):
            if button.get_active():
                self._type = type
        for type, descr in TYPES:
            radio = gtk.RadioButton(radio, descr)
            radio.connect("toggled", type_toggled, type)
            radio.show()
            if not self._type:
                self._type = type
            self._typevbox.pack_start(radio)

        self._window.show()

        self._result = False
        alias = type = None
        while True:
            gtk.main()
            if self._result:
                self._result = False
                type = self._type
                alias = self._alias.get_text().strip()
                if not alias:
                    iface.error("No alias provided!")
                    continue
                if alias in sysconf.get("channels", {}):
                    iface.error("Alias already in use!")
                    continue
                break
            alias = type = None
            break

        self._window.hide()

        return alias, type

# vim:ts=4:sw=4:et

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
from smart.util.strtools import strToBool
from smart.channel import *
from smart import *
import gobject, gtk
import textwrap
import os

class GtkChannels(object):

    def __init__(self, parent=None):

        self._changed = False

        self._window = gtk.Window()
        self._window.set_title("Channels")
        self._window.set_modal(True)
        self._window.set_transient_for(parent)
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=600, min_height=400)
        def delete(widget, event):
            gtk.main_quit()
            return True
        self._window.connect("delete-event", delete)

        vbox = gtk.VBox()
        vbox.set_border_width(10)
        vbox.set_spacing(10)
        vbox.show()
        self._window.add(vbox)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.show()
        vbox.add(sw)

        self._treemodel = gtk.ListStore(gobject.TYPE_INT,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING)
        self._treeview = gtk.TreeView(self._treemodel)
        self._treeview.set_rules_hint(True)
        self._treeview.show()
        sw.add(self._treeview)

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
        vbox.pack_start(bbox, expand=False)

        button = gtk.Button(stock="gtk-new")
        button.show()
        button.connect("clicked", lambda x: self.newChannel())
        bbox.pack_start(button)

        button = gtk.Button(stock="gtk-delete")
        button.show()
        def clicked(x):
            selection = self._treeview.get_selection()
            model, iter = selection.get_selected()
            if not iter:
                return
            alias = model.get_value(iter, 1)
            self.delChannel(alias)
        button.connect("clicked", clicked)
        bbox.pack_start(button)

        button = gtk.Button(stock="gtk-properties")
        button.show()
        def clicked(x):
            selection = self._treeview.get_selection()
            model, iter = selection.get_selected()
            if not iter:
                return
            alias = model.get_value(iter, 1)
            self.editChannel(alias)
        button.connect("clicked", clicked)
        bbox.pack_start(button)

        button = gtk.Button(stock="gtk-close")
        button.show()
        button.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(button)

    def fill(self):
        self._treemodel.clear()
        channels = sysconf.get("channels", ())
        for alias in channels:
            channel = channels[alias]
            self._treemodel.append((not strToBool(channel.get("disabled")),
                                    alias,
                                    channel.get("type", ""),
                                    channel.get("name", "")))

    def enableDisable(self):
        for row in self._treemodel:
            disabled = strToBool(sysconf.get(("channels", row[1], "disabled")))
            if row[0]:
                if disabled:
                    sysconf.remove(("channels", row[1], "disabled"))
                    self._changed = True
            else:
                if not disabled:
                    sysconf.set(("channels", row[1], "disabled"), "yes")
                    self._changed = True
            
    def show(self):
        self.fill()
        self._window.show()
        gtk.main()
        self._window.hide()
        self.enableDisable()
        return self._changed

    def newChannel(self):
        self.enableDisable()

        method = MethodSelector().show()
        if not method:
            return

        editor = ChannelEditor()

        if method == "manual":

            type = TypeSelector().show()
            if not type:
                return

            newchannel = {"type": type}
            if editor.show(None, newchannel, editalias=True):
                alias = newchannel["alias"]
                del newchannel["alias"]
                sysconf.set(("channels", alias), newchannel)
                self._changed = True

        elif method in ("descriptionpath", "descriptionurl"):

            if method == "descriptionpath":
                #dia = gtk.FileChooserDialog(
                #             action=gtk.FILE_CHOOSER_ACTION_OPEN,
                #             buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK,
                #                      gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
                dia = gtk.FileSelection("Select Channel Description")
                dia.hide_fileop_buttons()
                response = dia.run()
                filename = dia.get_filename()
                dia.destroy()
                if response != gtk.RESPONSE_OK:
                    return
                if not os.path.isfile(filename):
                    iface.error("File not found: %s" % filename)
                    return
                file = open(filename)
                data = file.read()
                file.close()
            elif method == "descriptionurl":
                url = iface.askInput("Description URL")
                if not url:
                    return
                ctrl = iface.getControl()
                succ, fail = ctrl.downloadURLs([url], "channel description")
                if fail:
                    iface.error("Unable to fetch channel description: %s"
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
                    sysconf.set(("channels", alias), newchannel)
                    self._changed = True

        elif method in ("detectmedia", "detectpath"):

            if method == "detectmedia":
                path = MountPointSelector().show()
                if not path:
                    return
            elif method == "detectpath":
                dia = gtk.FileSelection("Select Path")
                dia.hide_fileop_buttons()
                response = dia.run()
                path = dia.get_filename()
                dia.destroy()
                if response != gtk.RESPONSE_OK:
                    return
                if not os.path.isdir(path):
                    iface.error("Directory not found: %s" % path)
                    return

            foundchannel = False
            for newchannel in detectLocalChannels(path):
                foundchannel = True
                if editor.show(newchannel.get("alias"), newchannel,
                               editalias=True):
                    alias = newchannel["alias"]
                    del newchannel["alias"]
                    sysconf.set(("channels", alias), newchannel)
                    self._changed = True
            
            if not foundchannel:
                iface.error("No channels detected!")
                return

        if self._changed:
            self.fill()

    def editChannel(self, alias):
        self.enableDisable()
        channel = sysconf.get(("channels", alias), {})
        editor = ChannelEditor()
        if editor.show(alias, channel):
            sysconf.set(("channels", alias), channel)
            self._changed = True
            self.fill()

    def delChannel(self, alias):
        if sysconf.remove(("channels", alias)):
            self._changed = True
            self.fill()

class GtkChannelSelector(object):

    def __init__(self):

        self._window = gtk.Window()
        self._window.set_title("Select Channels")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        self._window.set_geometry_hints(min_width=600, min_height=400)
        def delete(widget, event):
            gtk.main_quit()
            return True
        self._window.connect("delete-event", delete)

        vbox = gtk.VBox()
        vbox.set_border_width(10)
        vbox.set_spacing(10)
        vbox.show()
        self._window.add(vbox)

        self._scrollwin = gtk.ScrolledWindow()
        self._scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self._scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self._scrollwin.show()
        vbox.add(self._scrollwin)

        self._treemodel = gtk.ListStore(gobject.TYPE_INT,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_STRING)
        self._treeview = gtk.TreeView(self._treemodel)
        self._treeview.set_rules_hint(True)
        self._treeview.show()
        self._scrollwin.add(self._treeview)

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
        vbox.pack_start(bbox, expand=False)

        button = gtk.Button(stock="gtk-ok")
        button.show()
        def clicked(x):
            self._result = True
            gtk.main_quit()
        button.connect("clicked", clicked)
        bbox.pack_start(button)

        button = gtk.Button(stock="gtk-cancel")
        button.show()
        button.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(button)

    def fill(self):
        self._treemodel.clear()
        channels = sysconf.get("channels", {})
        for alias in channels:
            channel = channels[alias]
            self._treemodel.append((False, alias,
                                    channel.get("type", ""),
                                    channel.get("name", "")))

    def show(self):
        self.fill()
        self._result = False
        self._window.show()
        gtk.main()
        self._window.hide()

        result = []
        if self._result == True:
            for row in self._treemodel:
                if row[0]:
                    result.append(row[1])

        return result

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

        vbox = gtk.VBox()
        vbox.set_border_width(10)
        vbox.set_spacing(10)
        vbox.show()
        self._window.add(vbox)

        self._table = gtk.Table()
        self._table.set_row_spacings(10)
        self._table.set_col_spacings(10)
        self._table.show()
        vbox.pack_start(self._table)

        sep = gtk.HSeparator()
        sep.show()
        vbox.pack_start(sep, expand=False)

        bbox = gtk.HButtonBox()
        bbox.set_spacing(10)
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.show()
        vbox.pack_start(bbox, expand=False)

        button = gtk.Button(stock="gtk-ok")
        button.show()
        def clicked(x):
            self._result = True
            gtk.main_quit()
        button.connect("clicked", clicked)
        bbox.pack_start(button)

        button = gtk.Button(stock="gtk-cancel")
        button.show()
        button.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(button)

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
            entry.set_value(int(text or 0))
        else:
            entry = gtk.Entry()
            entry.set_text(text)
        entry.set_property("sensitive", bool(editable))
        entry.show()
        if small or spin:
            if spin:
                entry.set_width_chars(8)
            else:
                entry.set_width_chars(20)
            align = gtk.Alignment(0.0, 0.5, 0.0, 0.0)
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

    def show(self, alias, channel, editalias=False):
        self._table.foreach(self._table.remove)

        # Basic fields
        self.addField("alias", "Alias", alias or "",
                      editable=editalias, small=True)
        self.addField("type", "Type", channel.get("type", ""),
                      editable=False, small=True)

        # Checkboxes
        enabled = gtk.CheckButton("Enabled")
        enabled.set_active(not strToBool(channel.get("disabled")))
        enabled.show()
        align = gtk.Alignment(0.0, 0.5)
        align.add(enabled)
        align.show()
        self._table.attach(align, 1, 2, self._fieldn, self._fieldn+1,
                           gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._fieldn += 1

        manual = gtk.CheckButton("Manual updates")
        manual.set_active(strToBool(channel.get("manual")))
        manual.show()
        align = gtk.Alignment(0.0, 0.5)
        align.add(manual)
        align.show()
        self._table.attach(align, 1, 2, self._fieldn, self._fieldn+1,
                           gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._fieldn += 1

        removable = gtk.CheckButton("Removable")
        removable.set_active(strToBool(channel.get("removable")))
        removable.show()
        align = gtk.Alignment(0.0, 0.5)
        align.add(removable)
        align.show()
        self._table.attach(align, 1, 2, self._fieldn, self._fieldn+1,
                           gtk.EXPAND|gtk.FILL, gtk.FILL)
        self._fieldn += 1

        # Other common fields:
        self.addField("name", "Name", channel.get("name", ""))

        # Specific fields:
        for key, name, descr in getChannelInfo(channel.get("type")).fields:
            tip = "\n".join(textwrap.wrap(text=descr, width=40))
            self.addField(key, name, channel.get(key, ""), tip=tip,
                          spin=(key == "priority"))

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
                if manual.get_active():
                    newchannel["manual"] = "yes"
                elif "manual" in channel:
                    del newchannel["manual"]
                if removable.get_active():
                    newchannel["removable"] = "yes"
                elif "removable" in channel:
                    del newchannel["removable"]
                try:
                    for key in self._fields:
                        if key != "type":
                            entry = self._fields[key]
                            value = entry.get_text().strip()
                            if key == "alias":
                                if not editalias:
                                    continue
                                if not value:
                                    raise Error, "Invalid alias!"
                                if (value != alias and 
                                    sysconf.has(("channels", value))):
                                    raise Error, "Alias already in use!"
                                if not alias:
                                    alias = value
                                newchannel[key] = value
                            elif not value and key in newchannel:
                                del newchannel[key]
                            else:
                                newchannel[key] = value
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

class TypeSelector(object):

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

        vbox = gtk.VBox()
        vbox.set_border_width(10)
        vbox.set_spacing(10)
        vbox.show()
        self._window.add(vbox)

        table = gtk.Table()
        table.set_row_spacings(10)
        table.set_col_spacings(10)
        table.show()
        vbox.pack_start(table)
        
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
        vbox.pack_start(sep, expand=False)

        bbox = gtk.HButtonBox()
        bbox.set_spacing(10)
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.show()
        vbox.pack_start(bbox, expand=False)

        self._ok = button = gtk.Button(stock="gtk-ok")
        button.show()
        def clicked(x):
            self._result = True
            gtk.main_quit()
        button.connect("clicked", clicked)
        bbox.pack_start(button)

        button = gtk.Button(stock="gtk-cancel")
        button.show()
        button.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(button)

    def show(self):
        self._typevbox.foreach(self._typevbox.remove)
        self._type = None

        radio = None
        def type_toggled(button, type):
            if button.get_active():
                self._type = type
        infos = [(info.name, type) for type, info in
                 getAllChannelInfos().items()]
        infos.sort()
        for name, type in infos:
            if not self._type:
                self._type = type
            radio = gtk.RadioButton(radio, name)
            radio.connect("activate", lambda x: self._ok.activate())
            radio.connect("toggled", type_toggled, type)
            radio.show()
            self._typevbox.pack_start(radio)

        self._window.show()

        self._result = False
        type = None
        while True:
            gtk.main()
            if self._result:
                type = self._type
                break
            type = None
            break

        self._window.hide()

        return type

class MethodSelector(object):

    def __init__(self):

        self._window = gtk.Window()
        self._window.set_title("New Channel")
        self._window.set_modal(True)
        self._window.set_position(gtk.WIN_POS_CENTER)
        def delete(widget, event):
            gtk.main_quit()
            return True
        self._window.connect("delete-event", delete)

        vbox = gtk.VBox()
        vbox.set_border_width(10)
        vbox.set_spacing(10)
        vbox.show()
        self._window.add(vbox)

        table = gtk.Table()
        table.set_row_spacings(10)
        table.set_col_spacings(10)
        table.show()
        vbox.pack_start(table)
        
        label = gtk.Label("Method:")
        label.set_alignment(1.0, 0.0)
        label.show()
        table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL)

        methodvbox = gtk.VBox()
        methodvbox.set_spacing(10)
        methodvbox.show()
        table.attach(methodvbox, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, gtk.FILL)

        sep = gtk.HSeparator()
        sep.show()
        vbox.pack_start(sep, expand=False)

        bbox = gtk.HButtonBox()
        bbox.set_spacing(10)
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.show()
        vbox.pack_start(bbox, expand=False)

        ok = button = gtk.Button(stock="gtk-ok")
        button.show()
        def clicked(x):
            self._result = True
            gtk.main_quit()
        button.connect("clicked", clicked)
        bbox.pack_start(button)

        button = gtk.Button(stock="gtk-cancel")
        button.show()
        button.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(button)

        radio = None
        self._method = None
        def method_toggled(button, method):
            if button.get_active():
                self._method = method
        for method, descr in [("manual",
                               "Provide channel information"),
                              ("descriptionpath",
                               "Read channel description from local path"),
                              ("descriptionurl",
                               "Read channel description from URL"),
                              ("detectmedia",
                               "Detect channel in media (CDROM, DVD, etc)"),
                              ("detectpath",
                               "Detect channel in local path")]:
            if not self._method:
                self._method = method
            radio = gtk.RadioButton(radio, descr)
            radio.connect("activate", lambda x: ok.activate())
            radio.connect("toggled", method_toggled, method)
            radio.show()
            methodvbox.pack_start(radio)


    def show(self):

        self._window.show()

        self._result = False
        method = None
        while True:
            gtk.main()
            if self._result:
                method = self._method
                break
            method = None
            break

        self._window.hide()

        return method

class MountPointSelector(object):

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

        vbox = gtk.VBox()
        vbox.set_border_width(10)
        vbox.set_spacing(10)
        vbox.show()
        self._window.add(vbox)

        table = gtk.Table()
        table.set_row_spacings(10)
        table.set_col_spacings(10)
        table.show()
        vbox.pack_start(table)
        
        label = gtk.Label("Media path:")
        label.set_alignment(1.0, 0.0)
        label.show()
        table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL)

        self._mpvbox = gtk.VBox()
        self._mpvbox.set_spacing(10)
        self._mpvbox.show()
        table.attach(self._mpvbox, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, gtk.FILL)

        sep = gtk.HSeparator()
        sep.show()
        vbox.pack_start(sep, expand=False)

        bbox = gtk.HButtonBox()
        bbox.set_spacing(10)
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.show()
        vbox.pack_start(bbox, expand=False)

        self._ok = button = gtk.Button(stock="gtk-ok")
        button.show()
        def clicked(x):
            self._result = True
            gtk.main_quit()
        button.connect("clicked", clicked)
        bbox.pack_start(button)

        button = gtk.Button(stock="gtk-cancel")
        button.show()
        button.connect("clicked", lambda x: gtk.main_quit())
        bbox.pack_start(button)

    def show(self):
        self._mpvbox.foreach(self._mpvbox.remove)
        self._mp = None

        radio = None
        def mp_toggled(button, mp):
            if button.get_active():
                self._mp = mp
        n = 0
        for media in iface.getControl().getMediaSet():
            mp = media.getMountPoint()
            if not self._mp:
                self._mp = mp
            radio = gtk.RadioButton(radio, mp)
            radio.connect("activate", lambda x: self._ok.activate())
            radio.connect("toggled", mp_toggled, mp)
            radio.show()
            self._mpvbox.pack_start(radio)
            n += 1

        if n == 0:
            iface.error("No local media found!")
            return None
        elif n == 1:
            return self._mp

        self._window.show()

        self._result = False
        mp = None
        while True:
            gtk.main()
            if self._result:
                mp = self._mp
                break
            mp = None
            break

        self._window.hide()

        return mp

# vim:ts=4:sw=4:et

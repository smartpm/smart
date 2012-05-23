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
from smart.interfaces.gtk import getPixbuf
from smart import *
from gi.repository import GObject, Gtk

class GtkPreferences(Gtk.Window):

    def __init__(self, parent=None):
        GObject.GObject.__init__(self)

        self.set_icon(getPixbuf("smart"))
        self.set_title(_("Smart Preferences"))
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_geometry_hints(min_width=400, min_height=300)

        self._vbox = Gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self.add(self._vbox)

        self._notebook = Gtk.Notebook()
        self._notebook.show()
        self._vbox.add(self._notebook)

        if Gtk.pygtk_version < (2,12,0):
            self._tooltips = Gtk.Tooltips()

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_border_width(5)
        sw.show()

        table = Gtk.Table()
        table.set_row_spacings(2)
        table.set_col_spacings(5)
        table.set_border_width(5)
        table.show()
        sw.add_with_viewport(table)

        def set_tooltip(widget, text):
            if Gtk.pygtk_version < (2,12,0):
                self._tooltips.set_tip(widget, text)
            else:
                widget.set_tooltip_text(text)

        self._remove_packages = Gtk.CheckButton(_("Remove Packages"))
        set_tooltip(self._remove_packages,
                    _("Remove downloaded packages after installation"))
        self._remove_packages.set_active(sysconf.get("remove-packages", True))
        self._remove_packages.show()
        table.attach(self._remove_packages, 0, 1, 0, 0+1,
                     Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)

        self._commit_stepped = Gtk.CheckButton(_("Commit Stepped"))
        set_tooltip(self._commit_stepped,
                    _("Split operations in steps before committing"))
        self._commit_stepped.set_active(sysconf.get("commit-stepped", False))
        self._commit_stepped.show()
        table.attach(self._commit_stepped, 0, 1, 1, 1+1,
                     Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)

        label = Gtk.Label(label=_("General"))
        self._notebook.append_page(sw, label)

        self._buttonbox = Gtk.HButtonBox()
        self._buttonbox.set_spacing(10)
        self._buttonbox.set_layout(Gtk.ButtonBoxStyle.END)
        self._buttonbox.show()
        self._vbox.pack_start(self._buttonbox, expand=False, fill=False)

        self._closebutton = Gtk.Button(stock="gtk-close")
        self._closebutton.show()
        self._closebutton.connect("clicked", lambda x: self.close())
        self._buttonbox.pack_start(self._closebutton, True, True, 0)

    def close(self):
        sysconf.set("remove-packages", self._remove_packages.get_active())
        sysconf.set("commit-stepped", self._commit_stepped.get_active())
        self.hide()

GObject.type_register(GtkPreferences)


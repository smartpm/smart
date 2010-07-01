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
import gobject, gtk, pango

class GtkLegend(gtk.Window):

    def __init__(self):
        gtk.Window.__init__(self)
        self.__gobject_init__()

        self.set_icon(getPixbuf("smart"))
        self.set_title(_("Icon Legend"))

        font = self.style.font_desc.copy()
        font.set_size(font.get_size()-pango.SCALE)

        boldfont = font.copy()
        boldfont.set_weight(pango.WEIGHT_BOLD)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self.add(self._vbox)

        attrslabel = pango.AttrList()
        attrslabel.insert(pango.AttrFontDesc(boldfont, 0, -1))

        label = gtk.Label(_("The following icons are used to indicate\nthe current status of a package:"))
        label.set_attributes(attrslabel)
        label.show()
        self._vbox.add(label)

        table = gtk.Table()
        table.set_row_spacings(2)
        table.set_col_spacings(5)
        table.set_border_width(5)
        table.show()
        self._vbox.add(table)
  
        row = 0
        for icon, legend in [
        (getPixbuf("package-install"),            _("Marked for installation")),
        (getPixbuf("package-reinstall"),          _("Marked for re-installation")),
        (getPixbuf("package-upgrade"),            _("Marked for upgrade")),
        (getPixbuf("package-downgrade"),          _("Marked for downgrade")),
        (getPixbuf("package-remove"),             _("Marked for removal")),
        (getPixbuf("package-available"),          _("Not installed")),
        (getPixbuf("package-new"),                _("Not installed (new)")),
        (getPixbuf("package-available-locked"),   _("Not installed (locked)")),
        (getPixbuf("package-installed"),          _("Installed")),
        (getPixbuf("package-installed-outdated"), _("Installed (upgradable)")),
        (getPixbuf("package-installed-locked"),   _("Installed (locked)")),
        (getPixbuf("package-broken"),             _("Broken")),
        ]:
            image = gtk.Image()
            image.set_from_pixbuf(icon)
            image.show()
            table.attach(image, 0, 1, row, row+1, gtk.FILL, gtk.FILL)
            label = gtk.Label(legend)
            label.set_alignment(0.0, 0.5)
            label.show()
            table.attach(label, 1, 2, row, row+1, gtk.FILL, gtk.FILL)
            row += 1
        
        self._buttonbox = gtk.HButtonBox()
        self._buttonbox.set_spacing(10)
        self._buttonbox.set_layout(gtk.BUTTONBOX_END)
        self._buttonbox.show()
        self._vbox.pack_start(self._buttonbox, expand=False, fill=False)

        self._closebutton = gtk.Button(stock="gtk-close")
        self._closebutton.show()
        self._closebutton.connect("clicked", lambda x: self.hide())
        self._buttonbox.pack_start(self._closebutton)

    def isVisible(self):
        return self.get_property("visible")

gobject.type_register(GtkLegend)


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
from smart.const import ERROR, WARNING, DEBUG
from smart.interfaces.gtk import getPixbuf
from smart import *
from gi.repository import Gtk, GObject
import locale

try:
    ENCODING = locale.getpreferredencoding()
except locale.Error:
    ENCODING = "C"

LONG_MESSAGE_LENGTH = 1024
LONG_MESSAGE_LINES = 8

class LongMessageDialog(Gtk.Dialog):
    """Scrolling version of Gtk.MessageDialog"""
    def __init__(self, parent=None, flags=0,
                 type=Gtk.MessageType.INFO,
                 buttons=Gtk.ButtonsType.NONE,
                 message_format=None):
        icon = Gtk.STOCK_DIALOG_INFO
        if type == Gtk.MessageType.ERROR:
            icon = Gtk.STOCK_DIALOG_ERROR
        btns = None
        if buttons == Gtk.ButtonsType.OK:
            btns = (Gtk.STOCK_OK, Gtk.ResponseType.OK)
        GObject.GObject.__init__(self, None, parent, flags, btns)
        hbox = Gtk.HBox()
        hbox.set_border_width(10)
        hbox.set_spacing(10)
        image = Gtk.Image()
        image.set_from_stock(icon, Gtk.IconSize.DIALOG)
        image.show()
        hbox.pack_start(image, expand=False, fill=False)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        text = Gtk.TextView()
        text.set_editable(False)
        text.modify_base(Gtk.StateType.NORMAL, self.style.bg[Gtk.StateType.NORMAL])
        text.set_wrap_mode(Gtk.WrapMode.WORD)
        text.get_buffer().set_text(message_format)
        text.show()
        sw.add(text)
        sw.show()
        hbox.pack_start(sw, expand=True, fill=True)
        hbox.show()
        self.vbox.pack_start(hbox, True, True, 0)

class GtkLog(Gtk.Window):

    def __init__(self):
        GObject.GObject.__init__(self)

        self.set_icon(getPixbuf("smart"))
        self.set_title(_("Log"))
        self.set_geometry_hints(min_width=400, min_height=300)
        self.set_modal(True)

        self._vbox = Gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self.add(self._vbox)

        self._scrollwin = Gtk.ScrolledWindow()
        self._scrollwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self._scrollwin.set_shadow_type(Gtk.ShadowType.IN)
        self._scrollwin.show()
        self._vbox.add(self._scrollwin)

        self._textview = Gtk.TextView()
        self._textview.set_editable(False)
        self._textview.show()
        self._scrollwin.add(self._textview)

        self._buttonbox = Gtk.HButtonBox()
        self._buttonbox.set_spacing(10)
        self._buttonbox.set_layout(Gtk.ButtonBoxStyle.END)
        self._buttonbox.show()
        self._vbox.pack_start(self._buttonbox, expand=False, fill=False)

        self._clearbutton = Gtk.Button(stock="gtk-clear")
        self._clearbutton.show()
        self._clearbutton.connect("clicked",
                                  lambda x: self.clearText())
        self._buttonbox.pack_start(self._clearbutton, True, True, 0)

        self._closebutton = Gtk.Button(stock="gtk-close")
        self._closebutton.show()
        self._closebutton.connect("clicked", lambda x: self.hide())
        self._buttonbox.pack_start(self._closebutton, True, True, 0)

    def clearText(self):
        self._textview.get_buffer().set_text("")
    
    def isVisible(self):
        return self.get_property("visible")

    def message(self, level, msg):
        prefix = {ERROR: _("error"), WARNING: _("warning"),
                  DEBUG: _("debug")}.get(level)
        buffer = self._textview.get_buffer()
        iter = buffer.get_end_iter()
        if not isinstance(msg, str):
            msg = msg.decode(ENCODING)
        if prefix:
            for line in msg.split("\n"):
                buffer.insert(iter, "%s: %s\n" % (prefix, line))
        else:
            buffer.insert(iter, msg)
        buffer.insert(iter, "\n")

        if level == ERROR:
            if (len(msg) > LONG_MESSAGE_LENGTH or
                msg.count("\n") > LONG_MESSAGE_LINES):
                gtk_MessageDialog = LongMessageDialog
            else:
                gtk_MessageDialog = Gtk.MessageDialog
                
            dialog = gtk_MessageDialog(self, flags=Gtk.DialogFlags.MODAL,
                                       type=Gtk.MessageType.ERROR,
                                       buttons=Gtk.ButtonsType.OK,
                                       message_format=msg)
            dialog.run()
            dialog.hide()
            del dialog
        else:
            self.show()

GObject.type_register(GtkLog)


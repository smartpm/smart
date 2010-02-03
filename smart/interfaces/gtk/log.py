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
import gtk, gobject
import locale

try:
    ENCODING = locale.getpreferredencoding()
except locale.Error:
    ENCODING = "C"

LONG_MESSAGE_LENGTH = 1024
LONG_MESSAGE_LINES = 8

class LongMessageDialog(gtk.Dialog):
    """Scrolling version of gtk.MessageDialog"""
    def __init__(self, parent=None, flags=0,
                 type=gtk.MESSAGE_INFO,
                 buttons=gtk.BUTTONS_NONE,
                 message_format=None):
        icon = gtk.STOCK_DIALOG_INFO
        if type == gtk.MESSAGE_ERROR:
            icon = gtk.STOCK_DIALOG_ERROR
        btns = None
        if buttons == gtk.BUTTONS_OK:
            btns = (gtk.STOCK_OK, gtk.RESPONSE_OK)
        gtk.Dialog.__init__(self, None, parent, flags, btns)
        hbox = gtk.HBox()
        hbox.set_border_width(10)
        hbox.set_spacing(10)
        image = gtk.Image()
        image.set_from_stock(icon, gtk.ICON_SIZE_DIALOG)
        image.show()
        hbox.pack_start(image, expand=False, fill=False)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        text = gtk.TextView()
        text.set_editable(False)
        text.modify_base(gtk.STATE_NORMAL, self.style.bg[gtk.STATE_NORMAL])
        text.set_wrap_mode(gtk.WRAP_WORD)
        text.get_buffer().set_text(message_format)
        text.show()
        sw.add(text)
        sw.show()
        hbox.pack_start(sw, expand=True, fill=True)
        hbox.show()
        self.vbox.pack_start(hbox)

class GtkLog(gtk.Window):

    def __init__(self):
        gtk.Window.__init__(self)
        self.__gobject_init__()

        self.set_icon(getPixbuf("smart"))
        self.set_title(_("Log"))
        self.set_geometry_hints(min_width=400, min_height=300)
        self.set_modal(True)

        self._vbox = gtk.VBox()
        self._vbox.set_border_width(10)
        self._vbox.set_spacing(10)
        self._vbox.show()
        self.add(self._vbox)

        self._scrollwin = gtk.ScrolledWindow()
        self._scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._scrollwin.set_shadow_type(gtk.SHADOW_IN)
        self._scrollwin.show()
        self._vbox.add(self._scrollwin)

        self._textview = gtk.TextView()
        self._textview.set_editable(False)
        self._textview.show()
        self._scrollwin.add(self._textview)

        self._buttonbox = gtk.HButtonBox()
        self._buttonbox.set_spacing(10)
        self._buttonbox.set_layout(gtk.BUTTONBOX_END)
        self._buttonbox.show()
        self._vbox.pack_start(self._buttonbox, expand=False, fill=False)

        self._clearbutton = gtk.Button(stock="gtk-clear")
        self._clearbutton.show()
        self._clearbutton.connect("clicked",
                                  lambda x: self.clearText())
        self._buttonbox.pack_start(self._clearbutton)

        self._closebutton = gtk.Button(stock="gtk-close")
        self._closebutton.show()
        self._closebutton.connect("clicked", lambda x: self.hide())
        self._buttonbox.pack_start(self._closebutton)

    def clearText(self):
        self._textview.get_buffer().set_text("")
    
    def isVisible(self):
        return self.get_property("visible")

    def message(self, level, msg):
        prefix = {ERROR: _("error"), WARNING: _("warning"),
                  DEBUG: _("debug")}.get(level)
        buffer = self._textview.get_buffer()
        iter = buffer.get_end_iter()
        if not isinstance(msg, unicode):
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
                gtk_MessageDialog = gtk.MessageDialog
                
            dialog = gtk_MessageDialog(self, flags=gtk.DIALOG_MODAL,
                                       type=gtk.MESSAGE_ERROR,
                                       buttons=gtk.BUTTONS_OK,
                                       message_format=msg)
            dialog.run()
            dialog.hide()
            del dialog
        else:
            self.show()

gobject.type_register(GtkLog)


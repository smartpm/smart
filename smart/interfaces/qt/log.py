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
from smart.interfaces.qt import getPixmap
from smart import *
import qt
import locale

try:
    ENCODING = locale.getpreferredencoding()
except locale.Error:
    ENCODING = "C"

class QtLog(qt.QDialog):

    def __init__(self, parent=None):
        qt.QDialog.__init__(self, parent)

        self.setIcon(getPixmap("smart"))
        self.setCaption(_("Log"))
        self.setMinimumSize(400, 300)
        #self.setModal(True)

        #self._vbox = gtk.VBox()
        #self._vbox.set_border_width(10)
        #self._vbox.set_spacing(10)
        #self._vbox.show()
        #self.add(self._vbox)
        self._vbox = qt.QVBoxLayout(self)

        #self._scrollwin = gtk.ScrolledWindow()
        #self._scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        #self._scrollwin.set_shadow_type(gtk.SHADOW_IN)
        #self._scrollwin.show()
        #self._vbox.add(self._scrollwin)
        sv = qt.QScrollView(self)
        sv.setVScrollBarMode(qt.QScrollView.AlwaysOn)
        sv.show()
        self._vbox.addWidget(sv)

        #self._textview = gtk.TextView()
        #self._textview.set_editable(False)
        #self._textview.show()
        #self._scrollwin.add(self._textview)
        self._textview = qt.QLabel(sv)
        self._textview.setMinimumSize(400, 300) # HACK
        self._textview.setSizePolicy(qt.QSizePolicy.Expanding,qt.QSizePolicy.Expanding)
        self._textview.show()
        
        #self._buttonbox = gtk.HButtonBox()
        #self._buttonbox.set_spacing(10)
        #self._buttonbox.set_layout(gtk.BUTTONBOX_END)
        #self._buttonbox.show()
        #self._vbox.pack_start(self._buttonbox, expand=False, fill=False)
        
        #self._clearbutton = gtk.Button(stock="gtk-clear")
        #self._clearbutton.show()
        #self._clearbutton.connect("clicked",
        #                          lambda x: self._textview.get_buffer()
        #                                                 .set_text(""))
        #self._buttonbox.pack_start(self._clearbutton)
        self._clearbutton = qt.QPushButton("Clear", self)
        self._clearbutton.show()
        qt.QObject.connect(self._clearbutton, qt.SIGNAL("clicked()"), self.clearText)
        self._vbox.addWidget(self._clearbutton)

        #self._closebutton = gtk.Button(stock="gtk-close")
        #self._closebutton.show()
        #self._closebutton.connect("clicked", lambda x: self.hide())
        #self._buttonbox.pack_start(self._closebutton)
        self._closebutton = qt.QPushButton("Close", self)
        self._closebutton.show()
        qt.QObject.connect(self._closebutton, qt.SIGNAL("clicked()"), self, qt.SLOT("hide()"))
        self._vbox.addWidget(self._closebutton)

        self._closebutton.setDefault(True)

    def clearText(self):
        self._textview.clear()
    
    def isVisible(self):
        return qt.QDialog.isVisible(self)

    def message(self, level, msg):
        prefix = {ERROR: _("error"), WARNING: _("warning"),
                  DEBUG: _("debug")}.get(level)
        buffer = self._textview.text()
        if not isinstance(msg, unicode):
            msg = msg.decode(ENCODING)
        if prefix:
            for line in msg.split("\n"):
                buffer += "%s: %s\n" % (prefix, line)
        else:
            buffer += msg
        buffer += "\n"
        self._textview.setText(buffer)

        if level == ERROR:
             response = qt.QMessageBox.critical(self, "", msg)
        else:
             self.show()

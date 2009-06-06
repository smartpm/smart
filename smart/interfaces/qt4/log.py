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

class BackgroundScrollView(qt.QScrollView):
    def __init__(self, parent):
        qt.QScrollView.__init__(self, parent)
        self.setSizePolicy(
            qt.QSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding))

    def drawContents(self, *args):
        if len(args)==1:
            return apply(qt.QFrame.drawContents, (self,)+args)
        else:
            painter, clipx, clipy, clipw, cliph = args
        color = self.eraseColor()
        painter.fillRect(clipx, clipy, clipw, cliph, qt.QBrush(color))
        qt.QScrollView.drawContents(self, painter, clipx, clipy, clipw, cliph)

class QtLog(qt.QDialog):

    def __init__(self, parent=None):
        qt.QDialog.__init__(self, parent)

        self.setIcon(getPixmap("smart"))
        self.setCaption(_("Log"))
        self.setMinimumSize(400, 300)
        #self.setModal(True)

        layout = qt.QVBoxLayout(self)
        layout.setResizeMode(qt.QLayout.FreeResize)

        self._vbox = qt.QVBox(self)
        self._vbox.setMargin(10)
        self._vbox.setSpacing(10)
        self._vbox.show()

        layout.add(self._vbox)

        self._scrollview = BackgroundScrollView(self._vbox)
        self._scrollview.setVScrollBarMode(qt.QScrollView.AlwaysOn)
        self._scrollview.setFrameStyle(qt.QFrame.StyledPanel | qt.QFrame.Sunken)
        self._scrollview.show()

        self._textview = qt.QLabel(self._scrollview.viewport())
        self._textview.setAlignment(qt.Qt.AlignTop)
        self._textview.setTextFormat(qt.Qt.LogText)
        self._textview.show()
        self._textview.adjustSize()
        
        self._textview.setEraseColor(self._scrollview.eraseColor())

        self._buttonbox = qt.QHBox(self._vbox)
        self._buttonbox.setSpacing(10)
        self._buttonbox.layout().addStretch(1)
        self._buttonbox.show()

        self._clearbutton = qt.QPushButton(_("Clear"), self._buttonbox)
        self._clearbutton.show()
        qt.QObject.connect(self._clearbutton, qt.SIGNAL("clicked()"), self.clearText)

        self._closebutton = qt.QPushButton(_("Close"), self._buttonbox)
        self._closebutton.show()
        qt.QObject.connect(self._closebutton, qt.SIGNAL("clicked()"), self, qt.SLOT("hide()"))

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
        self._textview.adjustSize()

        if level == ERROR:
            response = qt.QMessageBox.critical(self, "", msg)
        else:
            self.show()

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
from smart.interfaces.qt4 import getPixmap
from smart import *
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import locale

try:
    ENCODING = locale.getpreferredencoding()
except locale.Error:
    ENCODING = "C"

class BackgroundScrollView(QtGui.QScrollArea):
    def __init__(self, parent):
        QtGui.QScrollArea.__init__(self, parent)
        self.setSizePolicy(
            QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding))

    def drawContents(self, *args):
        if len(args)==1:
            return apply(QtGui.QFrame.drawContents, (self,)+args)
        else:
            painter, clipx, clipy, clipw, cliph = args
        color = self.eraseColor()
        painter.fillRect(clipx, clipy, clipw, cliph, QtGui.QBrush(color))
        QtGui.QScrollArea.drawContents(self, painter, clipx, clipy, clipw, cliph)

class QtLog(QtGui.QDialog):

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self.setWindowTitle(_("Log"))
        self.setMinimumSize(400, 300)
        #self.setModal(True)

        layout = QtGui.QVBoxLayout(self)
        #layout.setResizeMode(QtGui.QLayout.FreeResize)

        self._vbox = QtGui.QWidget(self)
        QtGui.QVBoxLayout(self._vbox)
        self._vbox.layout().setMargin(10)
        self._vbox.layout().setSpacing(10)
        self._vbox.show()

        layout.addWidget(self._vbox)

        self._scrollview = BackgroundScrollView(self._vbox)
        self._scrollview.setWidgetResizable(True)
        self._scrollview.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self._scrollview.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Sunken)
        self._scrollview.show()
        self._vbox.layout().addWidget(self._scrollview)

        self._textview = QtGui.QLabel(self._scrollview.viewport())
        self._textview.setAlignment(QtCore.Qt.AlignTop)
        self._textview.setTextFormat(QtCore.Qt.LogText)
        self._textview.setAutoFillBackground(True)
        self._textview.setBackgroundRole(QtGui.QPalette.Base)
        self._textview.show()
        self._textview.adjustSize()
        
        #self._textview.setEraseColor(self._scrollview.eraseColor())
        self._scrollview.setWidget(self._textview)

        self._buttonbox = QtGui.QWidget(self._vbox)
        QtGui.QHBoxLayout(self._buttonbox)
        self._buttonbox.layout().setSpacing(10)
        self._buttonbox.layout().addStretch(1)
        self._buttonbox.show()
        self._vbox.layout().addWidget(self._buttonbox)

        self._clearbutton = QtGui.QPushButton(_("Clear"), self._buttonbox)
        self._clearbutton.show()
        QtCore.QObject.connect(self._clearbutton, QtCore.SIGNAL("clicked()"), self.clearText)
        self._buttonbox.layout().addWidget(self._clearbutton)

        self._closebutton = QtGui.QPushButton(_("Close"), self._buttonbox)
        self._closebutton.show()
        QtCore.QObject.connect(self._closebutton, QtCore.SIGNAL("clicked()"), self, QtCore.SLOT("hide()"))
        self._buttonbox.layout().addWidget(self._closebutton)

        self._closebutton.setDefault(True)

    def clearText(self):
        self._textview.clear()
    
    def isVisible(self):
        return QtGui.QDialog.isVisible(self)

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
            response = QtGui.QMessageBox.critical(self, "", msg)
        else:
            self.show()

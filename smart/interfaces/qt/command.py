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
from smart.interfaces.qt.interface import QtInterface
from smart.interfaces.qt import getPixmap, centerWindow
from smart import *
import time
import qt

class QtCommandInterface(QtInterface):

    def __init__(self, ctrl, argv=None):
        QtInterface.__init__(self, ctrl, argv)
        self._status = QtStatus()

    def showStatus(self, msg):
        self._status.show(msg)
        while qt.QApplication.eventLoop().hasPendingEvents():
            qt.QApplication.eventLoop().processEvents(qt.QEventLoop.AllEvents)

    def hideStatus(self):
        self._status.hide()
        while qt.QApplication.eventLoop().hasPendingEvents():
            qt.QApplication.eventLoop().processEvents(qt.QEventLoop.AllEvents)

    def run(self, command=None, argv=None):
        result = QtInterface.run(self, command, argv)        
        self._status.wait()
        while self._log.isVisible():
            time.sleep(0.1)
            while qt.QApplication.eventLoop().hasPendingEvents():
                qt.QApplication.eventLoop().processEvents(qt.QEventLoop.AllEvents)
        return result

class QtStatus(object):

    def __init__(self):
        self._window = qt.QDialog()
        self._window.setIcon(getPixmap("smart"))
        self._window.setCaption(_("Status"))
        self._window.setModal(True)
        self._vbox = qt.QVBox(self._window)
        self._vbox.setMargin(20)

        self._label = qt.QLabel(self._vbox)
        self._label.show()

        self._lastshown = 0

    def show(self, msg):
        self._label.setText(msg)
        self._vbox.adjustSize()
        self._window.adjustSize()
        self._window.show()
        centerWindow(self._window)
        self._lastshown = time.time()
        while qt.QApplication.eventLoop().hasPendingEvents():
            qt.QApplication.eventLoop().processEvents(qt.QEventLoop.AllEvents)

    def hide(self):
        self._window.hide()

    def isVisible(self):
        return self._window.isVisible()

    def wait(self):
        while self.isVisible() and self._lastshown+3 > time.time():
            time.sleep(0.3)
            while qt.QApplication.eventLoop().hasPendingEvents():
                qt.QApplication.eventLoop().processEvents(qt.QEventLoop.AllEvents)

# vim:ts=4:sw=4:et

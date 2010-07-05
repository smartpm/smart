#
# Copyright (c) 2005 Canonical
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
from smart.interface import getImagePath
from smart import *
import os

try:
    import PyQt4 
except ImportError:
    from smart.const import DEBUG
    if sysconf.get("log-level") == DEBUG:
        import traceback
        traceback.print_exc()
    raise Error, _("System has no support for qt python interface")

def create(ctrl, command=None, argv=None):
    if command:
        from smart.interfaces.qt4.command import QtCommandInterface
        return QtCommandInterface(ctrl)
    else:
        from smart.interfaces.qt4.interactive import QtInteractiveInterface
        return QtInteractiveInterface(ctrl)


_pixmap = {}

def getPixmap(name):
    if name not in _pixmap:
        filename = getImagePath(name)
        if os.path.isfile(filename):
            pixmap = PyQt4.QtGui.QPixmap(filename)
            _pixmap[name] = pixmap
        else:
            raise Error, _("Image '%s' not found") % name
    return _pixmap[name]

def centerWindow(window):
    w = window.topLevelWidget()
    if w:
        scrn = PyQt4.QtGui.QApplication.desktop().screenNumber(w)
    elif PyQt4.QtGui.QApplication.desktop().isVirtualDesktop():
        scrn = PyQt4.QtGui.QApplication.desktop().screenNumber(PyQt4.QtGui.QCursor.pos())
    else:
        scrn = PyQt4.QtGui.QApplication.desktop().screenNumber(window)
    desk = PyQt4.QtGui.QApplication.desktop().availableGeometry(scrn)
    window.move((desk.width() - window.frameGeometry().width()) / 2, \
                (desk.height() - window.frameGeometry().height()) / 2)


# vim:ts=4:sw=4:et

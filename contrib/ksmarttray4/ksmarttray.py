#!/usr/bin/env python
#
# Copyright (c) 2008 Canonical, Inc.
#
# Written by Anders F Bjorklund <afb@users.sourceforge.net>
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
from smart.interfaces.qt4 import getPixmap
from smart import *
import os, sys, subprocess

NAME = "KDE Applet for Smart"
VERSION = "0.1"
AUTHORS = ["""Anders F Bjorklund <afb@users.sourceforge.net>"""]

try:
    from PyKDE4.kdecore import ki18n, KAboutData, KCmdLineArgs
    from PyKDE4.kdeui import KApplication, KMainWindow, KAboutApplicationDialog, KIcon
    from PyQt4.QtGui import QSystemTrayIcon, QMenu, QIcon
    from PyQt4.QtCore import QVariant
except RuntimeError:
    raise Error, _("Could not open a valid X display")
except ImportError:
    import smart
    from smart.const import DEBUG
    ctrl = smart.init()
    if sysconf.get("log-level") == DEBUG:
        import traceback
        traceback.print_exc()
    raise Error, _("System has no support for kde python interface")

def exit_applet(*args):
    # need to detach sysTray, or it will segfault
    sysTray.hide()
    sysTray.contextMenu().deleteLater()
    sysTray.deleteLater()
    app.quit()

SMART_HELPER = ["smart-helper-kde"]

def smart_gui(*args):
    pid = subprocess.Popen(SMART_HELPER + ["--gui"]).pid
    return

def smart_update(*args):
    pid = subprocess.Popen(SMART_HELPER + ["update", "--gui"]).pid
    return

def show_about(*args):
    dlg = KAboutApplicationDialog(aboutData, None)
    dlg.exec_()

aboutData = KAboutData("ksmarttray", "", ki18n(NAME), VERSION, ki18n(""),
            KAboutData.License_GPL_V2, ki18n("2008 Canonical, Inc."), 
            ki18n(""), "http://smartpm.org", "smart@labix.org")
for author in AUTHORS:
    name, email = author.rsplit(" ", 1)
    aboutData.addAuthor(ki18n(name), ki18n(""), email.strip("<>"), "")

KCmdLineArgs.init (sys.argv, aboutData)
app = KApplication()

import smart
ctrl = smart.init()

mainWindow = KMainWindow()
smart_icon = QIcon(getPixmap("smart"))
mainWindow.setWindowIcon(smart_icon)
sysTray = QSystemTrayIcon(smart_icon, None)
smart_image = getPixmap("smart").toImage()
aboutData.setProgramLogo(QVariant(smart_image))

menu = QMenu(None)
menu.addAction(KIcon("view-refresh"), "Check for updates", smart_update)
menu.addAction(smart_icon, "Launch Smart", smart_gui)
menu.addSeparator()
menu.addAction(KIcon("help-about"), "About", show_about)
menu.addAction(KIcon("application-exit"), "Quit", exit_applet)
sysTray.setContextMenu(menu)

sysTray.show()

app.exec_()

# vim:ts=4:sw=4:et

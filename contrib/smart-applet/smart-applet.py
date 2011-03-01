#!/usr/bin/env python
#
# Copyright (c) 2008 Canonical, Inc.
#
# Written by Mauricio Teixeira <mteixeira@webset.net>
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
from gnome import url_show
import os, sys, subprocess

NAME = "Gnome Applet for Smart"
VERSION = "0.1"
AUTHORS = ["""Mauricio Teixeira <mauricio.teixeira@gmail.com>""",
           """Anders F Bjorklund <afb@users.sourceforge.net>"""]

try:
    import pygtk
    pygtk.require("2.0")
    import gtk
except RuntimeError:
    raise Error, _("Could not open a valid X display")
except ImportError:
    import smart
    from smart.const import DEBUG
    ctrl = smart.init()
    if sysconf.get("log-level") == DEBUG:
        import traceback
        traceback.print_exc()
    raise Error, _("System has no support for gtk python interface")

def exit_applet(*args):
    gtk.main_quit()
    return

def show_popup_menu(icon, button, time, *data):
    if button == 3:
        menu.popup(None, None, None, 0, time)
    return

if os.path.exists("/usr/bin/console-helper"):
    SMART_HELPER = ["/usr/bin/smart-helper"]
else:
    SMART_HELPER = ["gksu", "--", "smart"]

def smart_gui(*args):
    pid = subprocess.Popen(SMART_HELPER + ["--gui"]).pid
    return

def smart_update(*args):
    pid = subprocess.Popen(SMART_HELPER + ["update", "--gui"]).pid
    return

def about(*args):
    license = """
            This program is free software; you can redistribute it and/or modify
            it under the terms of the GNU General Public License as published by
            the Free Software Foundation; either version 2 of the License, or
            (at your option) any later version.

            This program is distributed in the hope that it will be useful,
            but WITHOUT ANY WARRANTY; without even the implied warranty of
            MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
            GNU General Public License for more details.

            You should have received a copy of the GNU General Public License
            along with this program; if not, write to the Free Software
            Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
            """
    gtk.about_dialog_set_url_hook(lambda dialog, url: url_show(url))
    aboutdlg = gtk.AboutDialog()
    aboutdlg.set_logo(getPixbuf("smart"))
    aboutdlg.set_version(VERSION)
    aboutdlg.set_name(NAME)
    aboutdlg.set_copyright("2008 Canonical, Inc.")
    aboutdlg.set_authors(AUTHORS)
    aboutdlg.set_license(license)
    aboutdlg.set_website("http://smartpm.org")
    aboutdlg.run()
    aboutdlg.destroy()
    return

import smart
ctrl = smart.init()

app_window = gtk.StatusIcon()
app_window.set_from_pixbuf(getPixbuf("smart"))

app_window.connect("popup-menu", show_popup_menu)

menu_items = (
    ("Check for updates", smart_update),
    ("Launch Smart", smart_gui),
    None,
    ("About...", about),
    ("Exit", exit_applet),
    )

factory = gtk.IconFactory ()
factory.add_default ()
icon_set = gtk.IconSet(getPixbuf("smart"))
factory.add("smart-icon", icon_set)

menu = gtk.Menu()
action_update = gtk.Action("smart_update", "Check for updates", None, "gtk-refresh")
action_update.connect("activate", smart_update)
menuitem_update = action_update.create_menu_item()
menu.add(menuitem_update)
action_launch = gtk.Action("smart_gui", "Launch Smart", None, "smart-icon")
action_launch.connect("activate", smart_gui)
menuitem_launch = action_launch.create_menu_item()
menu.add(menuitem_launch)
menu.add(gtk.SeparatorMenuItem())
action_about = gtk.Action("about", "About", None, "gtk-about")
action_about.connect("activate", about)
menuitem_about = action_about.create_menu_item()
menu.add(menuitem_about)
action_quit = gtk.Action("exit_applet", "Quit", None, "gtk-quit")
action_quit.connect("activate", exit_applet)
menuitem_quit = action_quit.create_menu_item()
menu.add(menuitem_quit)

menu.show_all()
app_window.set_visible(True)

gtk.main()

# vim:ts=4:sw=4:et

#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Gepeto.
#
# Gepeto is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gepeto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gepeto; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from gepeto.interface import getImagePath
from gepeto import *
import os

try:
    import gtk
except ImportError:
    from gepeto.const import DEBUG
    if sysconf.get("log-level") == DEBUG:
        import traceback
        traceback.print_exc()
    raise Error, "system has no support for gtk python interface"

def create(interactive):
    if interactive:
        from gepeto.interfaces.gtk.interactive import GtkInteractiveInterface
        return GtkInteractiveInterface()
    else:
        from gepeto.interfaces.gtk.command import GtkCommandInterface
        return GtkCommandInterface()
    
_pixbuf = {}

def getPixbuf(name):
    if name not in _pixbuf:
        filename = getImagePath(name)
        if os.path.isfile(filename):
            pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
            _pixbuf[name] = pixbuf
        else:
            raise Error, "image '%s' not found"
    return _pixbuf[name]


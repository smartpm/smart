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


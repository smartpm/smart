from gettext import translation
import os

__all__ = ["sysconf", "iface", "Error", "_"]

class Error(Exception): pass

try:
    _ = translation("cpm").ugettext
except IOError:
    _ = lambda s: unicode(s)

class Proxy:
    def __init__(self, object=None):
        self.object = object
    def __getattr__(self, attr):
        return getattr(self.object, attr)
    def __repr__(self):
        return "<Proxy for '%s'>" % repr(self.object)

sysconf = Proxy()
iface = Proxy()

def init(opts=None):
    from cpm.const import DEBUG, INFO, WARNING, ERROR, CONFFILE
    from cpm.interface import createInterface
    from cpm.sysconfig import SysConfig
    from cpm.interface import Interface
    from cpm.control import Control

    sysconf.object = SysConfig()
    if opts and opts.log_level:
        level = {"error": ERROR, "warning": WARNING,
                 "debug": DEBUG, "info": INFO}.get(opts.log_level)
        if level is None:
            raise Error, "unknown log level"
        sysconf.set("log-level", level, soft=True)
    if opts and opts.data_dir:
        datadir = os.path.expanduser(opts.data_dir)
        sysconf.set("data-dir", datadir, soft=True)
    ctrl = Control(opts and opts.config_file)
    if opts.gui:
        ifacename = sysconf.get("default-gui", "gtk")
    elif opts and opts.interface:
        ifacename = opts.interface
    else:
        ifacename = "text"
    iface.object = createInterface(ifacename, not bool(opts.command))
    return ctrl

# vim:ts=4:sw=4:et

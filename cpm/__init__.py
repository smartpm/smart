from gettext import translation

__all__ = ["sysconf", "logger", "Error", "_"]

def init(_sysconf, _logger):
    global sysconf, logger
    sysconf = _sysconf
    logger = _logger
    import sys
    for name, module in sys.modules.items():
        if name.startswith("cpm.") or ".cpm." in name:
            if hasattr(module, "sysconf") and module.sysconf is None:
                module.sysconf = sysconf
            if hasattr(module, "logger") and module.logger is None:
                module.logger = logger

sysconf = None
logger = None

class Error(Exception): pass

try:
    _ = translation("cpm").ugettext
except IOError:
    _ = lambda s: unicode(s)

# vim:ts=4:sw=4:et

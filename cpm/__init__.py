from gettext import translation
import logging
import sys

__all__ = ["Error", "logger", "_"]

class Error(Exception): pass

def getlogger():
    class Formatter(logging.Formatter):
        def format(self, record):
            record.llevelname = record.levelname.lower()
            return logging.Formatter.format(self, record)
    formatter = Formatter("%(llevelname)s: %(message)s")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logger = logging.getLogger("cpm")
    logger.addHandler(handler)
    return logger

logger = getlogger()

try:
    _ = translation("cpm").ugettext
except IOError:
    _ = lambda s: unicode(s)

# vim:ts=4:sw=4:et

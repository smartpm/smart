from cpm.interfaces.images import __file__ as _images__file__
from cpm.const import ERROR, WARNING, INFO, DEBUG
from cpm import *
import sys, os

class Interface:

    def start(self):
        pass

    def finish(self):
        pass

    def run(self, ctrl):
        pass
    
    def showStatus(self, msg):
        pass

    def hideStatus(self):
        pass

    def askYesNo(self, question, default=False):
        return True

    def askContCancel(self, question, default=False):
        return True

    def askOkCancel(self, question, default=False):
        return True

    def confirmTransaction(self, trans):
        return True

    def confirmChange(self, oldchangeset, newchangeset):
        return True

    def error(self, msg):
        if sysconf.get("log-level", INFO) >= ERROR:
            self.message(ERROR, msg)

    def warning(self, msg):
        if sysconf.get("log-level", INFO) >= WARNING:
            self.message(WARNING, msg)

    def info(self, msg):
        if sysconf.get("log-level", INFO) >= INFO:
            self.message(INFO, msg)

    def debug(self, msg):
        if sysconf.get("log-level", INFO) >= DEBUG:
            self.message(DEBUG, msg)

    def message(self, level, msg):
        prefix = {ERROR: "error", WARNING: "warning",
                  DEBUG: "debug"}.get(level)
        if prefix:
            for line in msg.split("\n"):
                sys.stderr.write("%s: %s\n" % (prefix, line))
        else:
            sys.stderr.write("%s\n" % msg.rstrip())

def createInterface(name, interactive):
    try:
        xname = name.replace('-', '_').lower()
        cpm = __import__("cpm.interfaces."+xname)
        interfaces = getattr(cpm, "interfaces")
        interface = getattr(interfaces, xname)
    except (ImportError, AttributeError):
        if sysconf.get("log-level") == DEBUG:
            import traceback
            traceback.print_exc()
        raise Error, "invalid interface '%s'" % name
    return interface.create(interactive)

def getImagePath(name, _dirname=os.path.dirname(_images__file__)):
    return os.path.join(_dirname, name+".png")

# vim:ts=4:sw=4:et

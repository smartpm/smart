from cpm.const import DEBUG, INFO, WARNING, ERROR
from cpm.control import Control, ControlFeedback
from cpm.progress import RPMStyleProgress
from cpm.sysconfig import XMLSysConfig
from cpm.log import Logger

class CommandLineFeedback(ControlFeedback):

    def __init__(self):
        self._progress = RPMStyleProgress()

    def fetcherCreated(self, fetcher):
        fetcher.setProgress(self._progress)

    def cacheCreated(self, cache):
        cache.setProgress(self._progress)

    def packageManagerCreated(self, pm):
        pm.setProgress(self._progress)

def initCmdLine(opts=None):
    sysconf = XMLSysConfig()
    if opts:
        if opts.config_file:
            sysconf.set("config-file", opts.config_file)
        if opts.log_level:
            level = {"error": ERROR, "warning": WARNING,
                     "debug": DEBUG, "info": INFO}.get(opts.log_level)
            if level is None:
                raise Error, "unknown log level"
            sysconf.set("log-level", level)
    else:
        sysconf.set("log-level", WARNING)
    sysconf.load()
    from cpm import init
    init(sysconf, Logger())
    ctrl = Control(CommandLineFeedback())
    return ctrl

# vim:ts=4:sw=4:et

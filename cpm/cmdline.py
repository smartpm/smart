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

def initCmdLine(opts):
    sysconf = XMLSysConfig()
    if opts.conffile:
        sysconf.set("config-file", opts.conffile)
    if opts.loglevel:
        level = {"error": ERROR, "warning": WARNING,
                 "debug": DEBUG, "info": INFO}.get(opts.loglevel)
        if level is None:
            raise Error, "unknown log level"
        sysconf.set("log-level", level)
    sysconf.load()
    from cpm import init
    init(sysconf, Logger())
    ctrl = Control(CommandLineFeedback())
    return ctrl

# vim:ts=4:sw=4:et

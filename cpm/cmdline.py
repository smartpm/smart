from cpm.const import DEBUG, INFO, WARNING, ERROR, CONFFILE
from cpm.control import Control, ControlFeedback
from cpm.progress import RPMStyleProgress
from cpm.sysconfig import SysConfig
from cpm.report import Report
from cpm.log import Logger
import os

class TextFeedback(ControlFeedback):

    def __init__(self, ctrl):
        ControlFeedback.__init__(self, ctrl)
        self._progress = RPMStyleProgress()
        ctrl.getFetcher().setProgress(self._progress)
        ctrl.getCache().setProgress(self._progress)

    def packageManagerStarting(self, pm):
        pm.setProgress(self._progress)

    def confirmTransaction(self, trans):
        report = Report(trans.getCache(), trans.getChangeSet())
        report.compute()

        print
        if report.upgrading or report.installing:
            pkgs = report.upgrading.keys()+report.installing.keys()
            pkgs.sort()
            print "The following packages are being installed:"
            for pkg in pkgs:
                print "   ", pkg
                for upgpkg in report.upgrading.get(pkg, ()):
                    print "       Upgrades:", upgpkg
            print
        if report.upgraded or report.removed:
            print "The following packages are being removed:"
            pkgs = report.upgraded.keys()+report.removed.keys()
            pkgs.sort()
            for pkg in pkgs:
                print "   ", pkg
                for upgpkg in report.upgraded.get(pkg, ()):
                    print "       Upgraded by:", upgpkg

            print
        res = raw_input("Confirm changes (y/N)? ").strip()
        if res and res[0].lower() == "y":
            return True
        return False

def initCmdLine(opts=None):
    sysconf = SysConfig()
    from cpm import init
    if opts and opts.gui:
        from cpm.gui.gtk.logger import GtkLogger
        logger = GtkLogger()
    else:
        logger = Logger()
    init(sysconf, logger)
    ctrl = Control()
    if opts and opts.gui:
        from cpm.gui.gtk.feedback import GtkFeedback
        ctrl.setFeedback(GtkFeedback(ctrl))
    else:
        ctrl.setFeedback(TextFeedback(ctrl))
    ctrl.loadSysConf(opts and opts.config_file)
    if opts and opts.log_level:
        level = {"error": ERROR, "warning": WARNING,
                 "debug": DEBUG, "info": INFO}.get(opts.log_level)
        if level is None:
            raise Error, "unknown log level"
        sysconf.set("log-level", level, soft=True)
    return ctrl


# vim:ts=4:sw=4:et

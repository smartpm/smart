from cpm.gui.gtk.progress import GtkProgress
from cpm.const import DEBUG, INFO, WARNING, ERROR, CONFFILE
from cpm.control import Control, ControlFeedback
from cpm.progress import RPMStyleProgress
from cpm.sysconfig import SysConfig
from cpm.report import Report
from cpm.log import Logger
import os

class GtkFeedback(ControlFeedback):

    def __init__(self, ctrl):
        ControlFeedback.__init__(self, ctrl)
        self._progress = GtkProgress()
        ctrl.getFetcher().setProgress(self._progress)
        ctrl.getCache().setProgress(self._progress)

    def packageManagerStarting(self, pm):
        pm.setProgress(self._progress)

# vim:ts=4:sw=4:et

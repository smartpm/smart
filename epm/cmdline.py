from epm.fetcher import FetcherFeedback
from epm.progress import Progress, RPMStyleProgress
from epm import *
import os

def initCmdLine(ctrl):
    prog = RPMStyleProgress()
    ctrl.setProgress(RPMStyleProgress())
    ctrl.getFetcher().setFeedback(TextualFetcherFeedback())

class TextualFetcherFeedback(FetcherFeedback):

    def __init__(self):
        self.current = 0

    def starting(self, handler=None):
        pass

    def finished(self, handler=None):
        pass

    def error(self, handler, msg):
        print "Error: %s: %s" % (handler.getURL(), msg)

# vim:ts=4:sw=4:et

from gepeto.interfaces.text.progress import TextProgress
from gepeto.interface import Interface
from gepeto.fetcher import Fetcher
from gepeto.report import Report
import os

class TextInterface(Interface):

    def __init__(self):
        self._progress = TextProgress()

    def getProgress(self, obj, hassub=False):
        self._progress.setHasSub(hassub)
        self._progress.setFetcherMode(isinstance(obj, Fetcher))
        return self._progress

    def getSubProgress(self, obj):
        return self._progress

    def showStatus(self, msg):
        print msg

    def askYesNo(self, question, default=False):
        mask = default and "%s (Y/n)? " or "%s (y/N)? "
        res = raw_input(mask % question).strip().lower()
        print
        if res:
            return "yes".startswith(res)
        return default

    def askContCancel(self, question, default=False):
        mask = default and "%s (Continue/cancel): " or "%s (continue/Cancel)? "
        res = raw_input(mask % question).strip().lower()
        print
        if res and res != "c":
            return "continue".startswith(res)
        return default

    def askOkCancel(self, question, default=False):
        mask = default and "%s (Ok/cancel): " or "%s (ok/Cancel): "
        res = raw_input(mask % question).strip().lower()
        print
        if res:
            return "ok".startswith(res)
        return default

    def confirmTransaction(self, trans):
        report = Report(trans.getChangeSet())
        report.compute()

        print
        pkgs = report.upgrading.keys() + \
               report.downgrading.keys() + \
               report.installing.keys()
        if pkgs:
            pkgs.sort()
            print "The following packages are being installed:"
            for pkg in pkgs:
                print "   ", pkg
                for upgpkg in report.upgrading.get(pkg, ()):
                    print "       Upgrades:", upgpkg
                for upgpkg in report.downgrading.get(pkg, ()):
                    print "       Downgrades:", upgpkg
            print
        pkgs = report.upgraded.keys() + \
               report.downgraded.keys() + \
               report.removed.keys()
        if pkgs:
            pkgs.sort()
            print "The following packages are being removed:"
            for pkg in pkgs:
                print "   ", pkg
                for upgpkg in report.upgraded.get(pkg, ()):
                    print "       Upgraded by:", upgpkg
                for upgpkg in report.downgraded.get(pkg, ()):
                    print "       Downgraded by:", upgpkg

            print
        return self.askYesNo("Confirm changes")

# vim:ts=4:sw=4:et

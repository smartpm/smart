#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Gepeto.
#
# Gepeto is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gepeto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gepeto; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
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

    def confirmChangeSet(self, changeset):
        report = Report(changeset)
        report.compute()

        print
        pkgs = report.install.keys()
        if pkgs:
            pkgs.sort()
            print "The following packages are being installed:"
            for pkg in pkgs:
                if pkg.installed:
                    print "   ", pkg, "(reinstalled)"
                else:
                    print "   ", pkg
                for upgpkg in report.upgrading.get(pkg, ()):
                    print "       Upgrades:", upgpkg
                for upgpkg in report.downgrading.get(pkg, ()):
                    print "       Downgrades:", upgpkg
            print
        pkgs = report.removed.keys()
        if pkgs:
            pkgs.sort()
            print "The following packages are being removed:"
            for pkg in pkgs:
                print "   ", pkg
            print
        return self.askYesNo("Confirm changes", True)

    def insertRemovableChannels(self, channels):
        print
        print "Insert one or more of the following removable channels:"
        print
        for channel in channels:
            print "   ", channel.getName()
        print
        return self.askOkCancel("Continue", True)

# vim:ts=4:sw=4:et

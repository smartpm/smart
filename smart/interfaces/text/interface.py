#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from smart.interfaces.text.progress import TextProgress
from smart.interface import Interface, getScreenWidth
from smart.util.strtools import sizeToStr, printColumns
from smart.const import OPTIONAL, ALWAYS
from smart.fetcher import Fetcher
from smart.report import Report
from smart import *
import getpass
import sys
import os

class TextInterface(Interface):

    def __init__(self, ctrl):
        Interface.__init__(self, ctrl)
        self._progress = TextProgress()
        self._activestatus = False

    def getProgress(self, obj, hassub=False):
        self._progress.setHasSub(hassub)
        self._progress.setFetcherMode(isinstance(obj, Fetcher))
        return self._progress

    def getSubProgress(self, obj):
        return self._progress

    def showStatus(self, msg):
        if self._activestatus:
            print
        else:
            self._activestatus = True
        sys.stdout.write(msg)
        sys.stdout.flush()

    def hideStatus(self):
        if self._activestatus:
            self._activestatus = False
            print

    def askYesNo(self, question, default=False):
        self.hideStatus()
        mask = default and _("%s (Y/n): ") or _("%s (y/N): ")
        try:
            res = raw_input(mask % question).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print
            return False
        print
        if res:
            return (_("yes").startswith(res) and not
                    _("no").startswith(res))
        return default

    def askContCancel(self, question, default=False):
        self.hideStatus()
        if default:
            mask = _("%s (Continue/cancel): ")
        else:
            mask = _("%s (continue/Cancel): ")
        try:
            res = raw_input(mask % question).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print
            return False
        print
        if res:
            return (_("continue").startswith(res) and not
                    _("cancel").startswith(res))
        return default

    def askOkCancel(self, question, default=False):
        self.hideStatus()
        mask = default and _("%s (Ok/cancel): ") or _("%s (ok/Cancel): ")
        try:
            res = raw_input(mask % question).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print
            return False
        print
        if res:
            return (_("ok").startswith(res) and not
                    _("cancel").startswith(res))
        return default

    def confirmChangeSet(self, changeset):
        return self.showChangeSet(changeset, confirm=True)

    def askInput(self, prompt, message=None, widthchars=None, echo=True):
        print
        if message:
            print message
        prompt += ": "
        try:
            if echo:
                res = raw_input(prompt)
            else:
                res = getpass.getpass(prompt)
        except (KeyboardInterrupt, EOFError):
            res = ""
        print
        return res

    def askPassword(self, location, caching=OPTIONAL):
        self._progress.lock()
        passwd = Interface.askPassword(self, location, caching)
        self._progress.unlock()
        return passwd

    def insertRemovableChannels(self, channels):
        self.hideStatus()
        print
        print _("Insert one or more of the following removable channels:")
        print
        for channel in channels:
            print "   ", str(channel)
        print
        return self.askOkCancel(_("Continue?"), True)

    # Non-standard interface methods:
        
    def showChangeSet(self, changeset, keep=None, confirm=False):
        self.hideStatus()
        report = Report(changeset)
        report.compute()


        if not sysconf.get("explain-changesets", False):
            screenwidth = getScreenWidth()
            hideversion = sysconf.get("text-hide-version", len(changeset) > 40)
            def showPackages(pkgs, showrelations=None):
                if hideversion:
                    pkgs = [x.name for x in pkgs]
                pkgs.sort()
                printColumns(pkgs, indent=2, width=screenwidth)
        else:
            def being(pkg):
                if (pkg in report.installing or
                    pkg in report.upgrading or
                    pkg in report.downgrading):
                    return _("(installed)")
                elif pkg in report.upgraded:
                    return _("(upgraded)")
                elif pkg in report.removed:
                    return _("(removed)")
                elif pkg in report.downgraded:
                    return _("(downgraded)")
                else:
                    return "" # Shouldn't happen
            def showPackages(pkgs, showrelations=True):
                pkgs.sort()
                for pkg in pkgs:
                    channels = []
                    for loader in pkg.loaders:
                        channels.append(loader.getChannel().getAlias())
                        channels.sort()
                    print " ", pkg, ("[%s]" % ", ".join(channels))
                    if showrelations:
                        if pkg in report.upgrading:
                            print "   ", _("Upgrades:")
                            for upgpkg in report.upgrading[pkg]:
                                print "     ", upgpkg, being(upgpkg)
                        if pkg in report.downgrading:
                            print "   ", _("Downgrades:")
                            for dwnpkg in report.downgrading[pkg]:
                                print "     ", dwnpkg, being(dwnpkg)
                        if pkg in report.requires:
                            print "   ", _("Requires:")
                            for reqpkg in report.requires[pkg]:
                                print "     ", reqpkg, being(reqpkg)
                        if pkg in report.requiredby:
                            print "   ", _("Required By:")
                            for reqpkg in report.requiredby[pkg]:
                                print "     ", reqpkg, being(reqpkg)
                        if pkg in report.conflicts:
                            print "   ", _("Conflicts:")
                            for cnfpkg in report.conflicts[pkg]:
                                print "     ", cnfpkg, being(cnfpkg)

        print
        if keep:
            print _("Kept packages (%d):") % len(keep)
            showPackages(keep, False)
            print
        pkgs = report.upgrading.keys()
        if pkgs:
            print _("Upgrading packages (%d):") % len(pkgs)
            showPackages(pkgs)
            print
        pkgs = report.downgrading.keys()
        if pkgs:
            print _("Downgrading packages (%d):") % len(pkgs)
            showPackages(pkgs)
            print
        pkgs = report.installing.keys()
        if pkgs:
            print _("Installing packages (%d):") % len(pkgs)
            showPackages(pkgs)
            print
        pkgs = report.removed.keys()
        if pkgs:
            print _("Removing packages (%d):") % len(pkgs)
            showPackages(pkgs)
            print

        dsize = report.getDownloadSize() - report.getCachedSize()
        size = report.getInstallSize() - report.getRemoveSize()
        if dsize:
            sys.stdout.write(_("%s of package files are needed. ") %
                             sizeToStr(dsize))
        if size > 0:
            sys.stdout.write(_("%s will be used.") % sizeToStr(size))
        elif size < 0:
            size *= -1
            sys.stdout.write(_("%s will be freed.") % sizeToStr(size))
        if dsize or size:
            sys.stdout.write("\n\n")
        if confirm:
            return self.askYesNo(_("Confirm changes?"), True)
        return True

# vim:ts=4:sw=4:et

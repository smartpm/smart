#
# Copyright (c) 2005 Canonical
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
import tempfile
import sys, os
import codecs
import locale

from smart.util.filetools import setCloseOnExec
from smart.sorter import ChangeSetSorter
from smart.const import INSTALL, REMOVE
from smart.pm import PackageManager
from smart import sysconf, iface, Error, _


try:
    ENCODING = locale.getpreferredencoding()
except locale.Error:
    ENCODING = "ascii"


def get_public_key(header):
    return header.sprintf("%|DSAHEADER?{%{DSAHEADER:pgpsig}}:"
                          "{%|RSAHEADER?{%{RSAHEADER:pgpsig}}:"
                          "{%|SIGGPG?{%{SIGGPG:pgpsig}}:"
                          "{%|SIGPGP?{%{SIGPGP:pgpsig}}:"
                          "{(none)}|}|}|}|").split()[-1]


class RPMPackageManager(PackageManager):

    def commit(self, changeset, pkgpaths):

        prog = iface.getProgress(self, True)
        prog.start()
        prog.setTopic(_("Committing transaction..."))
        prog.set(0, len(changeset))
        prog.show()

        # Compute upgrading/upgraded packages
        upgrading = {}
        upgraded = {}
        for pkg in changeset.keys():
            if changeset.get(pkg) is INSTALL:
                upgpkgs = [upgpkg for prv in pkg.provides
                                  for upg in prv.upgradedby
                                  for upgpkg in upg.packages
                                  if upgpkg.installed]
                upgpkgs.extend([prvpkg for upg in pkg.upgrades
                                       for prv in upg.providedby
                                       for prvpkg in prv.packages
                                       if prvpkg.installed])
                if upgpkgs:
                    for upgpkg in upgpkgs:
                        # If any upgraded package will stay in the system,
                        # this is not really an upgrade for rpm.
                        if changeset.get(upgpkg) is not REMOVE:
                            break
                    else:
                        upgrading[pkg] = True
                        for upgpkg in upgpkgs:
                            upgraded[upgpkg] = True
                            if upgpkg in changeset:
                                del changeset[upgpkg]

        ts = getTS(True)

        flags = ts.setFlags(0)
        if sysconf.get("rpm-allfiles", False):
            flags |= rpm.RPMTRANS_FLAG_ALLFILES
        if sysconf.get("rpm-justdb", False):
            flags |= rpm.RPMTRANS_FLAG_JUSTDB
        if sysconf.get("rpm-noconfigs", False):
            flags |= rpm.RPMTRANS_FLAG_NOCONFIGS
        if (sysconf.get("rpm-nodocs", False) or
            sysconf.get("rpm-excludedocs", False)):
            flags |= rpm.RPMTRANS_FLAG_NODOCS
        if sysconf.get("rpm-nomd5", False):
            flags |= rpm.RPMTRANS_FLAG_NOMD5
        if sysconf.get("rpm-noscripts", False):
            flags |= rpm.RPMTRANS_FLAG_NOSCRIPTS
        if sysconf.get("rpm-notriggers", False):
            flags |= rpm.RPMTRANS_FLAG_NOTRIGGERS
        if sysconf.get("rpm-repackage", False):
            flags |= rpm.RPMTRANS_FLAG_REPACKAGE
        if sysconf.get("rpm-test", False):
            flags |= rpm.RPMTRANS_FLAG_TEST
        ts.setFlags(flags)

        dflags = ts.setDFlags(0)
        if sysconf.get("rpm-noupgrade", False):
            dflags |= rpm.RPMDEPS_FLAG_NOUPGRADE
        if sysconf.get("rpm-norequires", False):
            dflags |= rpm.RPMDEPS_FLAG_NOREQUIRES
        if sysconf.get("rpm-noconflicts", False):
            dflags |= rpm.RPMDEPS_FLAG_NOCONFLICTS
        if sysconf.get("rpm-noobsoletes", False):
            dflags |= rpm.RPMDEPS_FLAG_NOOBSOLETES
        if sysconf.get("rpm-noparentdirs", False):
            dflags |= rpm.RPMDEPS_FLAG_NOPARENTDIRS
        if sysconf.get("rpm-nolinktos", False):
            dflags |= rpm.RPMDEPS_FLAG_NOLINKTOS
        if sysconf.get("rpm-nosuggest", False):
            dflags |= rpm.RPMDEPS_FLAG_NOSUGGEST
        ts.setDFlags(dflags)

        # Set rpm verbosity level.
        levelname = sysconf.get('rpm-log-level')
        level = {
            'emerg':   rpm.RPMLOG_EMERG,
            'alert':   rpm.RPMLOG_ALERT,
            'crit':    rpm.RPMLOG_CRIT,
            'err':     rpm.RPMLOG_ERR,
            'warning': rpm.RPMLOG_WARNING,
            'notice':  rpm.RPMLOG_NOTICE,
            'info':    rpm.RPMLOG_INFO,
            'debug':   rpm.RPMLOG_DEBUG
        }.get(levelname)
        if level is not None:
            rpm.setVerbosity(level)

        # Set rpm output log file
        rpmlogfile = sysconf.get('rpm-log-file')
        if rpmlogfile is not None:
            try:
                rpmlog = open(rpmlogfile, 'w')
                rpm.setLogFile(rpmlog)
            except (IOError, OSError), e:
                raise Error, "%s: %s" % (rpmlogfile, unicode(e))

        # Let's help RPM, since it doesn't do a good
        # ordering job on erasures.
        try:
            sorter = ChangeSetSorter(changeset)
            sorted = sorter.getSorted()
            forcerpmorder = False
        except LoopError:
            lines = [_("Found unbreakable loops:")]
            for path in sorter.getLoopPaths(sorter.getLoops()):
                path = ["%s [%s]" % (pkg, op is INSTALL and "I" or "R")
                        for pkg, op in path]
                lines.append("    "+" -> ".join(path))
            lines.append(_("Will ask RPM to order it."))
            iface.error("\n".join(lines))
            sorted = [(pkg, changeset[pkg]) for pkg in changeset]
            forcerpmorder = True
        del sorter

        packages = 0
        reinstall = False
        for pkg, op in sorted:
            if op is INSTALL:
                if pkg.installed:
                    reinstall = True
                loader = [x for x in pkg.loaders if not x.getInstalled()][0]
                info = loader.getInfo(pkg)
                mode = pkg in upgrading and "u" or "i"
                path = pkgpaths[pkg][0]
                fd = os.open(path, os.O_RDONLY)
                try:
                    h = ts.hdrFromFdno(fd)
                    if sysconf.get("rpm-check-signatures", False):
                         if get_public_key(h) == '(none)':
                             raise rpm.error('package is not signed')
                except rpm.error, e:
                    os.close(fd)
                    raise Error, "%s: %s" % (os.path.basename(path), e)
                os.close(fd)
                ts.addInstall(h, (info, path), mode)
                packages += 1
            else:
                loader = [x for x in pkg.loaders if x.getInstalled()][0]
                offset = pkg.loaders[loader]
                try:
                    ts.addErase(offset)
                except rpm.error, e:
                    raise Error, "%s-%s: %s" % \
                                 (pkg.name, pkg.version, unicode(e))

        upgradednames = {}
        for pkg in upgraded:
            upgradednames[pkg.name] = True

        del sorted
        del upgraded
        del upgrading

        force = sysconf.get("rpm-force", False)
        if not force:
            probs = ts.check()
            if probs:
                problines = []
                for prob in probs:
                    name1 = "%s-%s-%s" % prob[0]
                    name2, version = prob[1]
                    if version:
                        sense = prob[2]
                        name2 += " "
                        if sense & rpm.RPMSENSE_LESS:
                            name2 += "<"
                        elif sense & rpm.RPMSENSE_GREATER:
                            name2 += ">"
                        if sense & rpm.RPMSENSE_EQUAL:
                            name2 += "="
                        name2 += " "
                        name2 += version
                    if prob[4] == rpm.RPMDEP_SENSE_REQUIRES:
                        line = _("%s requires %s") % (name1, name2)
                    else:
                        line = _("%s conflicts with %s") % (name1, name2)
                    problines.append(line)
                raise Error, "\n".join(problines)
        if sysconf.get("rpm-order"):
            ts.order()
        probfilter = rpm.RPMPROB_FILTER_OLDPACKAGE
        if force or reinstall:
            probfilter |= rpm.RPMPROB_FILTER_REPLACEPKG
            probfilter |= rpm.RPMPROB_FILTER_REPLACEOLDFILES
            probfilter |= rpm.RPMPROB_FILTER_REPLACENEWFILES
        ts.setProbFilter(probfilter)
        cb = RPMCallback(prog, upgradednames)
        cb.grabOutput(True)
        probs = None
        try:
            probs = ts.run(cb, None)
        finally:
            del getTS.ts
            cb.grabOutput(False)
            prog.setDone()
            if probs:
                raise Error, "\n".join([x[0] for x in probs])
            prog.stop()

class RPMCallback:
    def __init__(self, prog, upgradednames):
        self.prog = prog
        self.upgradednames = upgradednames
        self.data = {"item-number": 0}
        self.fd = None
        self.rpmout = None
        self.rpmoutbuffer = ""
        self.lasttopic = None
        self.topic = None

    def grabOutput(self, flag):
        if flag:
            if not self.rpmout:
                # Grab rpm output, but not the python one.
                self.stdout = sys.stdout
                self.stderr = sys.stderr
                writer = codecs.getwriter(ENCODING)
                reader = codecs.getreader(ENCODING)
                sys.stdout = writer(os.fdopen(os.dup(1), "w"),
                                    errors="replace")
                sys.stderr = writer(os.fdopen(os.dup(2), "w"),
                                    errors="replace")
                fd, rpmoutpath = tempfile.mkstemp("-smart-rpm-out.txt")
                os.dup2(fd, 1)
                os.dup2(fd, 2)
                os.close(fd)
                self.rpmout = reader(open(rpmoutpath))
                os.unlink(rpmoutpath)
        else:
            if self.rpmout:
                self._process_rpmout()
                os.dup2(sys.stdout.fileno(), 1)
                os.dup2(sys.stderr.fileno(), 2)
                sys.stdout = self.stdout
                sys.stderr = self.stderr
                del self.stdout
                del self.stderr
                self.rpmout.close()
                self.rpmout = None
                self.rpmoutbuffer = ""

    def _process_rpmout(self, tobuffer=False):
        if self.rpmout:
            output = self.rpmout.read()
            if output or not tobuffer and self.rpmoutbuffer:
                if tobuffer:
                    self.rpmoutbuffer += output
                else:
                    output = self.rpmoutbuffer+output
                    self.rpmoutbuffer = ""
                    if self.topic and self.topic != self.lasttopic:
                        self.lasttopic = self.topic
                        iface.info(self.topic)
                    iface.info(output)

    def __call__(self, what, amount, total, infopath, data):

        if self.rpmout:
            self._process_rpmout()

        if what == rpm.RPMCALLBACK_INST_OPEN_FILE:
            info, path = infopath
            pkgstr = str(info.getPackage())
            iface.debug(_("Processing %s in %s") % (pkgstr, path))
            self.topic = _("Output from %s:") % pkgstr
            self.fd = os.open(path, os.O_RDONLY)
            setCloseOnExec(self.fd)
            return self.fd
        
        elif what == rpm.RPMCALLBACK_INST_CLOSE_FILE:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None

        elif what == rpm.RPMCALLBACK_INST_START:
            info, path = infopath
            pkg = info.getPackage()
            self.data["item-number"] += 1
            self.prog.add(1)
            self.prog.setSubTopic(infopath, _("Installing %s") % pkg.name)
            self.prog.setSub(infopath, 0, 1, subdata=self.data)
            self.prog.show()

        elif (what == rpm.RPMCALLBACK_TRANS_PROGRESS or
              what == rpm.RPMCALLBACK_INST_PROGRESS):
            self.prog.setSub(infopath or "trans", amount, total,
                             subdata=self.data)
            self.prog.show()

        elif what == rpm.RPMCALLBACK_TRANS_START:
            self.prog.setSubTopic("trans", _("Preparing..."))
            self.prog.setSub("trans", 0, 1)
            self.prog.show()

        elif what == rpm.RPMCALLBACK_TRANS_STOP:
            self.prog.setSubDone("trans")
            self.prog.show()

        elif what == rpm.RPMCALLBACK_UNINST_START:
            self.topic = _("Output from %s:") % infopath
            subkey =  "R*"+infopath
            self.data["item-number"] += 1
            self.prog.add(1)
            if infopath in self.upgradednames:
                topic = _("Cleaning %s") % infopath
            else:
                topic = _("Removing %s") % infopath
            self.prog.setSubTopic(subkey, topic)
            self.prog.setSub(subkey, 0, 1, subdata=self.data)
            self.prog.show()

        elif what == rpm.RPMCALLBACK_UNINST_STOP:
            self.topic = None
            subkey = "R*"+infopath
            if not self.prog.getSub(subkey):
                self.data["item-number"] += 1
                self.prog.add(1)
                if infopath in self.upgradednames:
                    topic = _("Cleaning %s") % infopath
                else:
                    topic = _("Removing %s") % infopath
                self.prog.setSubTopic(subkey, topic)
                self.prog.setSub(subkey, 1, 1, subdata=self.data)
            else:
                self.prog.setSubDone(subkey)
            self.prog.show()

from smart.backends.rpm.base import rpm, getTS

# vim:ts=4:sw=4:et

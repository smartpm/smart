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
#from gepeto.backends.rpm.rpmver import splitarch
from gepeto.backends.rpm.crpmver import splitarch
from gepeto.pm import PackageManager
from gepeto import *
import sys, os
import errno
import fcntl
import rpm

class RPMPackageManager(PackageManager):

    def commit(self, install, remove, pkgpaths):

        prog = iface.getProgress(self, True)
        prog.start()
        prog.setTopic("Committing transaction...")
        prog.show()

        # Compute upgrading/upgraded packages
        upgrading = {}
        upgraded = {}
        for pkg in install:
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    upgd = []
                    for prvpkg in prv.packages:
                        if prvpkg.installed:
                            if prvpkg not in remove:
                                break
                            upgd.append(prvpkg)
                    else:
                        if upgd:
                            upgrading[pkg] = True
                            upgraded.update(dict.fromkeys(upgd))
        ts = rpm.ts(sysconf.get("rpm-root", "/"))
        packages = 0
        reinstall = False
        for pkg in install:
            if pkg.installed:
                reinstall = True
            loader = [x for x in pkg.loaders if not x.getInstalled()][0]
            info = loader.getInfo(pkg)
            mode = pkg in upgrading and "u" or "i"
            path = pkgpaths[pkg][0]
            fd = os.open(path, os.O_RDONLY)
            h = ts.hdrFromFdno(fd)
            os.close(fd)
            ts.addInstall(h, (info, path), mode)
            packages += 1
        for pkg in remove:
            if pkg not in upgraded:
                version = pkg.version
                if ":" in version:
                    version = version[version.find(":")+1:]
                version, arch = splitarch(version)
                try:
                    ts.addErase("%s-%s" % (pkg.name, version))
                except rpm.error, e:
                    raise Error, "%s-%s: %s" % (pkg.name, pkg.version, str(e))
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
                    line = "%s requires %s" % (name1, name2)
                else:
                    line = "%s conflicts with %s" % (name1, name2)
                problines.append(line)
            raise Error, "\n".join(problines)
        ts.order()
        probfilter = rpm.RPMPROB_FILTER_OLDPACKAGE
        if reinstall:
            probfilter |= rpm.RPMPROB_FILTER_REPLACEPKG
            probfilter |= rpm.RPMPROB_FILTER_REPLACEOLDFILES
        ts.setProbFilter(probfilter)
        prog.set(0, packages or 1)
        cb = RPMCallback(prog)
        cb.grabOutput(True)
        probs = ts.run(cb, None)
        cb.grabOutput(False)
        prog.setDone()
        if probs:
            raise Error, "\n".join([x[0] for x in probs])
        prog.stop()

class RPMCallback:
    def __init__(self, prog):
        self.data = {"item-number": 0}
        self.prog = prog
        self.fd = None
        self.rpmout = None
        self.lasttopic = None
        self.topic = None

    def grabOutput(self, flag):
        if flag:
            if not self.rpmout:
                # Grab rpm output, but not the python one.
                sys.stdout = os.fdopen(os.dup(1), "w")
                sys.stderr = os.fdopen(os.dup(2), "w")
                self.stdout = sys.stdout
                self.stderr = sys.stderr
                pipe = os.pipe()
                os.dup2(pipe[1], 1)
                os.dup2(pipe[1], 2)
                os.close(pipe[1])
                self.rpmout = pipe[0]
                flags = fcntl.fcntl(self.rpmout, fcntl.F_GETFL, 0)
                flags |= os.O_NONBLOCK
                fcntl.fcntl(self.rpmout, fcntl.F_SETFL, flags)
        else:
            if self.rpmout:
                self._rpmout()
                os.dup2(sys.stdout.fileno(), 1)
                os.dup2(sys.stderr.fileno(), 2)
                #sys.stdout.close()
                #sys.stderr.close()
                sys.stdout = self.stdout
                sys.stderr = self.stderr
                del self.stdout
                del self.stderr
                os.close(self.rpmout)
                self.rpmout = None

    def _rpmout(self):
        if self.rpmout:
            try:
                output = os.read(self.rpmout, 8192)
            except OSError, e:
                if e[0] != errno.EWOULDBLOCK:
                    raise
            else:
                if output:
                    if self.topic != self.lasttopic:
                        self.lasttopic = self.topic
                        iface.info(self.topic)
                    iface.info(output)

    def __call__(self, what, amount, total, infopath, data):

        self._rpmout()

        if what == rpm.RPMCALLBACK_INST_OPEN_FILE:
            info, path = infopath
            pkgstr = str(info.getPackage())
            iface.debug("Processing %s in %s" % (pkgstr, path))
            self.topic = "Output from %s:" % pkgstr
            self.fd = os.open(path, os.O_RDONLY)
            flags = fcntl.fcntl(self.fd, fcntl.F_GETFD, 0)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fd, fcntl.F_SETFD, flags)
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
            self.prog.setSubTopic(infopath, pkg.name)
            self.prog.setSub(infopath, 0, 1, subdata=self.data)
            self.prog.show()

        elif (what == rpm.RPMCALLBACK_TRANS_PROGRESS or
              what == rpm.RPMCALLBACK_INST_PROGRESS):
            self.prog.setSub(infopath or "trans", amount, total,
                             subdata=self.data)
            self.prog.show()

        elif what == rpm.RPMCALLBACK_TRANS_START:
            self.prog.setSubTopic("trans", "Preparing...")
            self.prog.setSub("trans", 0, 1)
            self.prog.show()

        elif what == rpm.RPMCALLBACK_TRANS_STOP:
            self.prog.setSubDone("trans")
            self.prog.show()

# vim:ts=4:sw=4:et

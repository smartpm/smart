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
import threading
import tempfile
import sys, os
import signal
import errno
import shlex

from smart.const import Enum, INSTALL, REMOVE
from smart.sorter import ElementSorter
from smart.pm import PackageManager
from smart.cache import PreRequires
from smart import sysconf, iface, _


# Part of the logic in this file was based on information found in APT.

UNPACK = Enum("UNPACK")
CONFIG = Enum("CONFIG")

DEBIAN_FRONTEND = "DEBIAN_FRONTEND"
APT_LISTCHANGES_FRONTEND = "APT_LISTCHANGES_FRONTEND"


class DebSorter(ElementSorter):

    def __init__(self, changeset=None):
        ElementSorter.__init__(self)
        if changeset:
            self.setChangeSet(changeset)

    def setChangeSet(self, changeset):
        # Set of priorities we use in this sorter.
        HIGH, MEDIUM, LOW = range(3)

        # XXX The organization here sucks a bit. :-(  We should clean this
        #     up, perhaps by refactoring this code into separate methods.
        self.reset()
        for pkg in changeset:
            op = changeset[pkg]
            if op is INSTALL:
                unpack = (pkg, UNPACK)
                config = (pkg, CONFIG)
                self.addSuccessor(unpack, config, HIGH)
            else:
                remove = (pkg, REMOVE)
                self.addElement(remove)

            # Unpacking or unconfiguring of a package must happen after
            # its pre-dependencies are configured, or before they are
            # unconfigured.  We do the same for normal dependencies
            # (non-pre) in an advisory fashion.
            for req in pkg.requires:
                if isinstance(req, PreRequires):
                    req_type_priority = MEDIUM
                else:
                    req_type_priority = LOW
                relations = []
                def add_relation(pred, succ, priority=MEDIUM):
                    relations.append((pred, succ, priority))
                for prv in req.providedby:
                    for prvpkg in prv.packages:
                        if changeset.get(prvpkg) is INSTALL:
                            if op is INSTALL:
                                # reqpkg=INSTALL, prvpkg=INSTALL
                                # ------------------------------
                                # When the package requiring a dependency and
                                # the package providing a dependency are both
                                # being installed, the unpack of the dependency
                                # must necessarily happen before the config of
                                # the dependent, and in pre-depends the unpack
                                # of the dependent must necessarily happen
                                # after the config of the dependency.
                                add_relation((prvpkg, UNPACK), config)
                                add_relation((prvpkg, CONFIG), config)
                                add_relation((prvpkg, CONFIG), unpack,
                                             req_type_priority)
                            else:
                                # reqpkg=REMOVE, prvpkg=INSTALL
                                # -----------------------------
                                # When the package requiring a dependency is
                                # being removed, and the package providing the
                                # dependency is being installed, the unpack
                                # of the dependency must necessarily happen
                                # before the unconfiguration of the dependent,
                                # and on pre-requires the configuration of the
                                # dependency must happen before the
                                # unconfiguration of the dependent.
                                add_relation((prvpkg, UNPACK), remove)
                                add_relation((prvpkg, CONFIG), remove,
                                             req_type_priority)
                        elif prvpkg.installed:
                            if changeset.get(prvpkg) is not REMOVE:
                                break
                            if op is INSTALL:
                                # reqpkg=INSTALL, prvpkg=REMOVE
                                # ------------------------------
                                # When the package providing the dependency
                                # is being removed, it may only be used by
                                # the dependent package before the former is
                                # removed from the system.  This means that
                                # for both dependencies and pre-dependencies
                                # the removal must happen before the
                                # configuration.
                                add_relation(config, (prvpkg, REMOVE))
                            else:
                                # reqpkg=REMOVE, prvpkg=REMOVE
                                # ------------------------------
                                # When both the package requiring the dependency
                                # and the one providing it are being removed,
                                # the removal of pre-dependencies must
                                # necessarily be done before the dependency
                                # removal.  We can't enforce it for dependencies
                                # because it would easily create a cycle.
                                add_relation(remove, (prvpkg, REMOVE),
                                             req_type_priority)
                    else:
                        continue
                    break
                else:
                    for relation in relations:
                        self.addSuccessor(*relation)

            if op is INSTALL:
                # That's a nice trick. We put the removed package after
                # the upgrading package installation. If this relation
                # is broken, it means that some conflict has moved the
                # upgraded package removal due to a loop. In these cases
                # we remove the package before the upgrade process,
                # otherwise we do the upgrade and forget about the
                # removal which is after.
                upgpkgs = [upgpkg for prv in pkg.provides
                                  for upg in prv.upgradedby
                                  for upgpkg in upg.packages]
                upgpkgs.extend([prvpkg for upg in pkg.upgrades
                                       for prv in upg.providedby
                                       for prvpkg in prv.packages])
                for upgpkg in upgpkgs:
                    if changeset.get(upgpkg) is REMOVE:
                        self.addSuccessor(unpack, (upgpkg, REMOVE), MEDIUM)

                # Conflicted packages being removed must go in
                # before this package's unpacking.
                cnfpkgs = [prvpkg for cnf in pkg.conflicts
                                  for prv in cnf.providedby
                                  for prvpkg in prv.packages
                                   if prvpkg.name != pkg.name]
                cnfpkgs.extend([cnfpkg for prv in pkg.provides
                                       for cnf in prv.conflictedby
                                       for cnfpkg in cnf.packages
                                        if cnfpkg.name != pkg.name])
                for cnfpkg in cnfpkgs:
                    if changeset.get(cnfpkg) is REMOVE:
                        self.addSuccessor((cnfpkg, REMOVE), unpack, HIGH)


class DebPackageManager(PackageManager):

    MAXPKGSPEROP = 50

    def commit(self, changeset, pkgpaths):

        prog = iface.getProgress(self)
        prog.start()
        prog.setTopic(_("Committing transaction..."))
        prog.show()

        # Compute upgraded packages
        upgraded = {}
        for pkg in changeset.keys():
            if changeset[pkg] is INSTALL:
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
                        assert changeset.get(upgpkg) is REMOVE, \
                               "Installing %s while %s is kept?" % \
                               (pkg, upgpkg)
                        assert upgpkg not in upgraded, \
                               "Two packages (%s and %s) upgrading the " \
                               "same installed package (%s)!?" % \
                               (pkg, upgraded[upgpkg], upgpkg)
                        upgraded[upgpkg] = pkg

        sorter = DebSorter(changeset)

        sorted = sorter.getSorted()

        prog.set(0, len(sorted))

        baseargs = shlex.split(sysconf.get("dpkg", "dpkg"))

        opt = sysconf.get("deb-root")
        if opt:
            baseargs.append("--root=%s" % opt)
        opt = sysconf.get("deb-admindir")
        if opt:
            baseargs.append("--admindir=%s" % opt)
        opt = sysconf.get("deb-instdir")
        if opt:
            baseargs.append("--instdir=%s" % opt)
        opt = sysconf.get("deb-simulate")
        if opt:
            baseargs.append("--simulate")

        PURGE = object()

        if sysconf.get("deb-purge"):
            for i in range(len(sorted)):
                pkg, op = sorted[i]
                if op is REMOVE and not upgraded.get(pkg):
                    sorted[i] = pkg, PURGE

        if sysconf.get("deb-non-interactive"):
            old_debian_frontend = os.environ.get(DEBIAN_FRONTEND)
            old_apt_lc_frontend = os.environ.get(APT_LISTCHANGES_FRONTEND)
            os.environ[DEBIAN_FRONTEND] = "noninteractive"
            os.environ[APT_LISTCHANGES_FRONTEND] = "none"
            baseargs.append("--force-confold")

        if sysconf.get("pm-iface-output"):
            output = tempfile.TemporaryFile()
        else:
            output = sys.stdout

        print >>output

        done = {}
        error = None
        while sorted:

            pkgs = []
            op = sorted[0][1]
            while (sorted and sorted[0][1] is op and
                   len(pkgs) < self.MAXPKGSPEROP):
                pkg, op = sorted.pop(0)
                if op is REMOVE and upgraded.get(pkg) in done:
                    continue
                done[pkg] = True
                opname = {REMOVE: "remove", PURGE: "purge", CONFIG: "config",
                          UNPACK: "unpack", INSTALL: "install"}
                print >>output, "[%s] %s" % (opname[op], pkg)
                pkgs.append(pkg)

            if not pkgs:
                continue

            args = baseargs[:]

            if op is REMOVE:
                args.append("--force-depends")
                args.append("--force-remove-essential")
                args.append("--remove")
            elif op is PURGE:
                args.append("--force-remove-essential")
                args.append("--purge")
            elif op is UNPACK:
                args.append("--unpack")
            elif op is CONFIG:
                args.append("--force-depends")
                args.append("--force-remove-essential")
                args.append("--configure")

            if op is UNPACK:
                for pkg in pkgs:
                    args.append(pkgpaths[pkg][0])
            else:
                for pkg in pkgs:
                    args.append(pkg.name)

            thread_name = threading.currentThread().getName()
            if thread_name == "MainThread":
                quithandler = signal.signal(signal.SIGQUIT, signal.SIG_IGN)
                inthandler  = signal.signal(signal.SIGINT, signal.SIG_IGN)

            output.flush()

            status = self.dpkg(args, output)

            if thread_name == "MainThread":
                signal.signal(signal.SIGQUIT, quithandler)
                signal.signal(signal.SIGINT,  inthandler)

            if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
                if os.WIFSIGNALED(status) and os.WTERMSIG(status):
                    error = _("Sub-process %s has received a "
                              "segmentation fault") % args[0]
                elif os.WIFEXITED(status):
                    error = _("Sub-process %s returned an error code "
                              "(%d)") % (args[0], os.WEXITSTATUS(status))
                else:
                    error = _("Sub-process %s exited unexpectedly") % args[0]
                break

            print >>output # Should avoid that somehow.
            prog.add(len(pkgs))
            prog.show()
            print >>output # Should avoid that somehow.

        if output != sys.stdout:
            output.flush()
            output.seek(0)
            data = output.read(8192)
            while data:
                iface.showOutput(data)
                data = output.read(8192)
            output.close()

        if sysconf.get("deb-non-interactive"):
            if old_debian_frontend is None:
                del os.environ[DEBIAN_FRONTEND]
            else:
                os.environ[DEBIAN_FRONTEND] = old_debian_frontend
            if old_apt_lc_frontend is None:
                del os.environ[APT_LISTCHANGES_FRONTEND]
            else:
                os.environ[APT_LISTCHANGES_FRONTEND] = old_apt_lc_frontend

        if error:
            iface.error(error)

        prog.setDone()
        prog.stop()

    def dpkg(self, argv, output):
        pid = os.fork()
        if not pid:
            if output != sys.stdout:
                output_fd = output.fileno()
                os.dup2(output_fd, 1)
                os.dup2(output_fd, 2)
            #print >>output, " ".join(argv)
            try:
                os.execvp(argv[0], argv)
            except OSError, e:
                output.write("%s: %s\n" % (argv[0], str(e)))
            os._exit(1)

        output.flush()

        while True:
            try:
                _pid, status = os.waitpid(pid, 0)
            except OSError, e:
                if e.errno != errno.EINTR:
                    raise
            else:
                if _pid == pid:
                    break

        return status


# vim:ts=4:sw=4:et

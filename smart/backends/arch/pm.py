#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# Archlinux module written by Cody Lee (aka. platinummonkey) <platinummonkey@archlinux.us>
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
from smart.const import INSTALL, REMOVE
from smart.pm import PackageManager
from smart.sorter import ChangeSetSorter
from smart import *
import commands

class ArchPackageManager(PackageManager):

    def commit(self, changeset, pkgpaths):
        upgrades = {}
        depchkoff = {}
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
                        # For each package that is to be upgraded
                        # Check for remove operations and delete them
                        if changeset.get(upgpkg) is not REMOVE:
                            break
                    else:
                        upgrades[pkg] = True
                        for upgpkg in upgpkgs:
                            if upgpkg in changeset and pkg.name != upgpkg.name:
                                # pacman doesn't remove pkgs of a different name
                                # during an upgrade even if one provides the other
                                depchkoff[upgpkg] = True
                            elif upgpkg in changeset:
                                del changeset[upgpkg]

        prog = iface.getProgress(self, True)
        prog.start()
        prog.setTopic(_("Committing transaction..."))
        prog.set(0, len(changeset))
        prog.show()

        sorted = ChangeSetSorter(changeset).getSorted()

        for pkg, op in sorted:
            depchk = depchkoff.get(pkg) and "d" or ""            
            if op == INSTALL and upgrades.get(pkg):
                prog.setSubTopic(pkg, _("Upgrading %s") % pkg.name)
                prog.setSub(pkg, 0, 1, 1)
                prog.show()
                status, output = commands.getstatusoutput("pacman -U%s %s" %
                                                          (depchk, pkgpaths[pkg][0]))
                prog.setSubDone(pkg)
                prog.show()
                if status != 0:
                    iface.warning(_("Got status %d upgrading %s:") % (status, pkg))
                    iface.warning(output)
                else:
                    iface.debug(_("Upgrading %s:") % pkg)
                    iface.debug(output)
            elif op == INSTALL:
                prog.setSubTopic(pkg, _("Installing %s") % pkg.name)
                prog.setSub(pkg, 0, 1, 1)
                prog.show()
                status, output = commands.getstatusoutput("pacman -U%s %s" %
                                                          (depchk, pkgpaths[pkg][0]))
                prog.setSubDone(pkg)
                prog.show()
                if status != 0:
                    iface.warning(_("Got status %d installing %s:") % (status, pkg))
                    iface.warning(output)
                else:
                    iface.debug(_("Installing %s:") % pkg)
                    iface.debug(output)
            elif op == REMOVE:
                prog.setSubTopic(pkg, _("Removing %s") % pkg.name)
                prog.setSub(pkg, 0, 1, 1)
                prog.show()
                status, output = commands.getstatusoutput("pacman -R%s %s" %
                                                          (depchk, pkg.name))
                prog.setSubDone(pkg)
                prog.show()
                if status != 0:
                    iface.warning(_("Got status %d removing %s:") % (status, pkg))
                    iface.warning(output)
                else:
                    iface.debug(_("Removing %s:") % pkg)
                    iface.debug(output)
            else:
                iface.warning(_("Operation ( %s ) not handled on package ( %s )"
                              % (op, pkg.name)))

        prog.setDone()
        prog.stop()
# vim:ts=4:sw=4:et

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
from smart.matcher import MasterMatcher
from smart.option import OptionParser
from smart import *
import string
import re

USAGE="smart check [options] [package] ..."

DESCRIPTION="""
This command will check relations of the given installed
packages. If no packages are given, all installed packages
will be checked. Use the 'fix' command to fix broken
relations.
"""

EXAMPLES="""
smart check
smart check pkgname
smart check '*kgna*'
smart check pkgname-1.0
smart check pkgname-1.0-1
smart check pkgname1 pkgname2
"""

def parse_options(argv):
    parser = OptionParser(usage=USAGE,
                          description=DESCRIPTION,
                          examples=EXAMPLES)
    parser.add_option("--stepped", action="store_true",
                      help="split operation in steps")
    parser.add_option("--urls", action="store_true",
                      help="dump needed urls and don't commit operation")
    parser.add_option("--download", action="store_true",
                      help="download packages and don't commit operation")
    parser.add_option("--force", action="store_true",
                      help="do not ask for confirmation")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts):

    ctrl.reloadChannels()
    cache = ctrl.getCache()

    if opts.args:
        pkgs = {}
        for arg in opts.args:
            matcher = MasterMatcher(arg)
            fpkgs = [pkg for pkg in matcher.filter(cache.getPackages())
                     if pkg.installed]
            if not fpkgs:
                raise Error, "'%s' matches no installed packages" % arg
            pkgs.update(dict.fromkeys(fpkgs, True))
        pkgs = pkgs.keys()
    else:
        pkgs = [pkg for pkg in cache.getPackages() if pkg.installed]

    pkgs.sort()

    problems = False
    coexistchecked = {}
    for pkg in pkgs:
        for req in pkg.requires:
            for prv in req.providedby:
                for prvpkg in prv.packages:
                    if prvpkg.installed:
                        break
                else:
                    continue
                break
            else:
                iface.info("Unsatisfied dependency: %s requires %s" %
                           (pkg, req))
                problems = True

        for cnf in pkg.conflicts:
            for prv in cnf.providedby:
                for prvpkg in prv.packages:
                    if prvpkg.installed:
                        iface.info("Unsatisfied dependency: "
                                   "%s conflicts with %s" % (pkg, prvpkg))
                        problems = True

        namepkgs = cache.getPackages(pkg.name)
        for namepkg in namepkgs:
            if (namepkg, pkg) in coexistchecked:
                continue
            coexistchecked[(pkg, namepkg)] = True
            if (namepkg.installed and namepkg is not pkg and
                not pkg.coexists(namepkg)):
                iface.info("Package %s can't coexist with %s" %
                           (namepkg, pkg))
                problems = True

    return problems

# vim:ts=4:sw=4:et

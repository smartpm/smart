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
from smart.util.strtools import isGlob
from smart.matcher import MasterMatcher
from smart.option import OptionParser
from smart.cache import Provides, PreRequires
from smart import *
import fnmatch
import string
import re

USAGE="smart query [options] [package] ..."

DESCRIPTION="""
This command allows querying the known packages in many
different ways. Check also the 'search' command.
"""

EXAMPLES="""
smart query pkgname
smart query '*kgnam*'
smart query pkgname-1.0
smart query pkgname --show-requires
smart query --requires libpkg.so --show-providedby
smart query --installed
smart query --summary ldap
"""

def parse_options(argv, help=None):
    if help:
        parser = OptionParser(help=help)
    else:
        parser = OptionParser(usage=USAGE,
                              description=DESCRIPTION,
                              examples=EXAMPLES)
    parser.add_option("--installed", action="store_true",
                      help="consider only installed packages")
    parser.add_option("--provides", action="append", default=[], metavar="DEP",
                      help="show only packages providing the given dependency")
    parser.add_option("--requires", action="append", default=[], metavar="DEP",
                      help="show only packages requiring the given dependency")
    parser.add_option("--conflicts", action="append", default=[], metavar="DEP",
                      help="show only packages conflicting with the given "
                           "dependency")
    parser.add_option("--upgrades", action="append", default=[], metavar="DEP",
                      help="show only packages upgrading the given dependency")
    parser.add_option("--name", action="append", default=[], metavar="STR",
                      help="show only packages which match given name")
    parser.add_option("--summary", action="append", default=[], metavar="STR",
                      help="show only packages which match given summary")
    parser.add_option("--description", action="append", default=[], metavar="STR",
                      help="show only packages which match given description")
    parser.add_option("--hide-version", action="store_true",
                      help="hide package version")
    parser.add_option("--show-summary", action="store_true",
                      help="show package summaries")
    parser.add_option("--show-provides", action="store_true",
                      help="show provides for the given packages")
    parser.add_option("--show-requires", action="store_true",
                      help="show requires for the given packages")
    parser.add_option("--show-prerequires", action="store_true",
                      help="show requires selecting only pre-dependencies")
    parser.add_option("--show-upgrades", action="store_true",
                      help="show upgrades for the given packages")
    parser.add_option("--show-conflicts", action="store_true",
                      help="show conflicts for the given packages")
    parser.add_option("--show-providedby", action="store_true",
                      help="show packages providing dependencies")
    parser.add_option("--show-requiredby", action="store_true",
                      help="show packages requiring provided information")
    parser.add_option("--show-upgradedby", action="store_true",
                      help="show packages upgrading provided information")
    parser.add_option("--show-conflictedby", action="store_true",
                      help="show packages conflicting with provided information")
    parser.add_option("--show-priority", action="store_true",
                      help="show package priority")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(ctrl, opts, updatecache=True):

    if updatecache:
        ctrl.updateCache()

    cache = ctrl.getCache()
    if not opts.args:
        packages = cache.getPackages()[:]
    else:
        packages = []
        for arg in opts.args:
            matcher = MasterMatcher(arg)
            packages.extend(matcher.filter(cache.getPackages()))

    if opts.installed:
        packages = [pkg for pkg in packages if pkg.installed]

    whoprovides = []
    for name in opts.provides:
        if '=' in name:
            name, version = name.split('=')
        else:
            version = None
        if isGlob(name):
            p = re.compile(fnmatch.translate(name), re.I)
            for prv in cache.getProvides():
                if p.match(prv.name):
                    whoprovides.append(Provides(prv.name, version))
        else:
            whoprovides.append(Provides(name, version))
    whorequires = []
    for name in opts.requires:
        if '=' in name:
            name, version = name.split('=')
        else:
            version = None
        if isGlob(name):
            p = re.compile(fnmatch.translate(name), re.I)
            for req in cache.getRequires():
                if p.match(req.name):
                    whorequires.append(Provides(req.name, version))
        else:
            whorequires.append(Provides(name, version))
    whoupgrades = []
    for name in opts.upgrades:
        if '=' in name:
            name, version = name.split('=')
        else:
            version = None
        if isGlob(name):
            p = re.compile(fnmatch.translate(name), re.I)
            for upg in cache.getUpgrades():
                if p.match(upg.name):
                    whoupgrades.append(Provides(upg.name, version))
        else:
            whoupgrades.append(Provides(name, version))
    whoconflicts = []
    for name in opts.conflicts:
        if '=' in name:
            name, version = name.split('=')
        else:
            version = None
        if isGlob(name):
            p = re.compile(fnmatch.translate(name), re.I)
            for cnf in cache.getConflicts():
                if p.match(cnf.name):
                    whoconflicts.append(Provides(cnf.name, version))
        else:
            whoconflicts.append(Provides(name, version))

    if whoprovides or whorequires or whoupgrades or whoconflicts:
        newpackages = {}
        for whoprv in whoprovides:
            for prv in cache.getProvides(whoprv.name):
                if not whoprv.version or prv.name == prv.version:
                    for pkg in prv.packages:
                        if pkg in packages:
                            newpackages[pkg] = True
        for whoreq in whorequires:
            for req in cache.getRequires(whoreq.name):
                if req.matches(whoreq):
                    for pkg in req.packages:
                        if pkg in packages:
                            newpackages[pkg] = True
        for whoupg in whoupgrades:
            for upg in cache.getUpgrades(whoupg.name):
                if upg.matches(whoupg):
                    for pkg in upg.packages:
                        if pkg in packages:
                            newpackages[pkg] = True
        for whocnf in whoconflicts:
            for cnf in cache.getConflicts(whocnf.name):
                if cnf.matches(whocnf):
                    for pkg in cnf.packages:
                        if pkg in packages:
                            newpackages[pkg] = True
        packages = newpackages.keys()

    hasname = []
    for token in opts.name:
        token = fnmatch.translate(token)[:-1].replace(r"\ ", " ")
        token = r"\s+".join(token.split())
        hasname.append(re.compile(token, re.I))
    hassummary = []
    for token in opts.summary:
        token = fnmatch.translate(token)[:-1].replace(r"\ ", " ")
        token = r"\s+".join(token.split())
        hassummary.append(re.compile(token, re.I))
    hasdescription = []
    for token in opts.description:
        token = fnmatch.translate(token)[:-1].replace(r"\ ", " ")
        token = r"\s+".join(token.split())
        hasdescription.append(re.compile(token, re.I))

    if hasname or hassummary or hasdescription:
        newpackages = {}
        for pkg in cache.getPackages():
            for pattern in hasname:
                if pattern.search(pkg.name):
                    newpackages[pkg] = True
            if hassummary or hasdescription:
                info = pkg.loaders.keys()[0].getInfo(pkg)
                for pattern in hassummary:
                    if pattern.search(info.getSummary()):
                        newpackages[pkg] = True
                for pattern in hasdescription:
                    if pattern.search(info.getDescription()):
                        newpackages[pkg] = True
        packages = newpackages.keys()

    packages.sort()
    for pkg in packages:
        if opts.hide_version:
            print pkg.name,
        else:
            print pkg,
        if opts.show_priority:
            print "{%s}" % pkg.getPriority(),
        if opts.show_summary:
            info = pkg.loaders.keys()[0].getInfo(pkg)
            print "-", info.getSummary(),
        print
        if pkg.provides and (opts.show_provides or whoprovides):
            pkg.provides.sort()
            first = True
            for prv in pkg.provides:
                if whoprovides:
                    for whoprv in whoprovides:
                        if (prv.name == whoprv.name and
                            (not whoprv.version or
                             prv.version == whoprv.version)):
                            break
                    else:
                        continue
                if first:
                    first = False
                    print "  Provides:"
                print "   ", prv
                if opts.show_requiredby and prv.requiredby:
                    print "      Required By:"
                    for req in prv.requiredby:
                        req.packages.sort()
                        for reqpkg in req.packages:
                            if opts.installed and not reqpkg.installed:
                                continue
                            if isinstance(req, PreRequires):
                                print "       ", "%s (%s) [pre]" % \
                                      (reqpkg, prv)
                            else:
                                if opts.hide_version:
                                    name = reqpkg.name
                                else:
                                    name = str(reqpkg)
                                print "       ", "%s (%s)" % (name, prv)
                if opts.show_upgradedby and prv.upgradedby:
                    print "      Upgraded By:"
                    for upg in prv.upgradedby:
                        upg.packages.sort()
                        for upgpkg in upg.packages:
                            if opts.installed and not upgpkg.installed:
                                continue
                            if opts.hide_version:
                                name = upgpkg.name
                            else:
                                name = str(upgpkg)
                            print "       ", "%s (%s)" % (name, prv)
                if opts.show_conflictedby and prv.conflictedby:
                    print "      Conflicted By:"
                    for cnf in prv.conflictedby:
                        cnf.packages.sort()
                        for cnfpkg in cnf.packages:
                            if opts.installed and not cnfpkg.installed:
                                continue
                            if opts.hide_version:
                                name = cnfpkg.name
                            else:
                                name = str(cnfpkg)
                            print "       ", "%s (%s)" % (name, prv)
        if pkg.requires and (opts.show_requires or opts.show_prerequires
                             or whorequires):
            pkg.requires.sort()
            first = True
            for req in pkg.requires:
                if opts.show_prerequires and not isinstance(req, PreRequires):
                    continue
                if whorequires:
                    for whoreq in whorequires:
                        if req.matches(whoreq):
                            break
                    else:
                        continue
                if first:
                    first = False
                    print "  Requires:"
                if isinstance(req, PreRequires):
                    print "   ", req, "[pre]"
                else:
                    print "   ", req
                if opts.show_providedby and req.providedby:
                    print "      Provided By:"
                    for prv in req.providedby:
                        prv.packages.sort()
                        for prvpkg in prv.packages:
                            if opts.installed and not prvpkg.installed:
                                continue
                            if opts.hide_version:
                                name = prvpkg.name
                            else:
                                name = str(prvpkg)
                            print "       ", "%s (%s)" % (name, prv)
        if pkg.upgrades and (opts.show_upgrades or whoupgrades):
            pkg.upgrades.sort()
            first = True
            for upg in pkg.upgrades:
                if whoupgrades:
                    for whoupg in whoupgrades:
                        if upg.matches(whoupg):
                            break
                    else:
                        continue
                if first:
                    first = False
                    print "  Upgrades:"
                print "   ", upg
                if opts.show_providedby and upg.providedby:
                    print "      Provided By:"
                    for prv in upg.providedby:
                        prv.packages.sort()
                        for prvpkg in prv.packages:
                            if opts.installed and not prvpkg.installed:
                                continue
                            if opts.hide_version:
                                name = prvpkg.name
                            else:
                                name = str(prvpkg)
                            print "       ", "%s (%s)" % (name, prv)
        if pkg.conflicts and (opts.show_conflicts or whoconflicts):
            pkg.conflicts.sort()
            first = True
            for cnf in pkg.conflicts:
                if whoconflicts:
                    for whocnf in whoconflicts:
                        if cnf.matches(whocnf):
                            break
                    else:
                        continue
                if first:
                    first = False
                    print "  Conflicts:"
                print "   ", cnf
                if opts.show_providedby and cnf.providedby:
                    print "      Provided By:"
                    for prv in cnf.providedby:
                        prv.packages.sort()
                        for prvpkg in prv.packages:
                            if opts.installed and not prvpkg.installed:
                                continue
                            if opts.hide_version:
                                name = prvpkg.name
                            else:
                                name = str(prvpkg)
                            print "       ", "%s (%s)" % (name, prv)

# vim:ts=4:sw=4:et

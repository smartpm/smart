from gepeto.matcher import MasterMatcher
from gepeto.option import OptionParser
from gepeto.cache import Provides, PreRequires
from gepeto import *
import string
import re

USAGE="gpt query [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    parser.add_option("--installed", action="store_true",
                      help="consider only installed packages")
    parser.add_option("--provides", action="store_true",
                      help="show provides for the given packages")
    parser.add_option("--requires", action="store_true",
                      help="show requires for the given packages")
    parser.add_option("--prerequires", action="store_true",
                      help="show requires selecting only pre-dependencies")
    parser.add_option("--upgrades", action="store_true",
                      help="show upgrades for the given packages")
    parser.add_option("--conflicts", action="store_true",
                      help="show conflicts for the given packages")
    parser.add_option("--providedby", action="store_true",
                      help="show packages providing dependencies")
    parser.add_option("--requiredby", action="store_true",
                      help="show packages requiring provided information")
    parser.add_option("--upgradedby", action="store_true",
                      help="show packages upgrading provided information")
    parser.add_option("--conflictedby", action="store_true",
                      help="show packages conflicting with provided information")
    parser.add_option("--whoprovides", action="append", default=[], metavar="DEP",
                      help="show only packages providing the given dependency")
    parser.add_option("--whorequires", action="append", default=[], metavar="DEP",
                      help="show only packages requiring the given dependency")
    parser.add_option("--whoconflicts", action="append", default=[], metavar="DEP",
                      help="show only packages conflicting with the given "
                           "dependency")
    parser.add_option("--whoupgrades", action="append", default=[], metavar="DEP",
                      help="show only packages upgrading the given dependency")
    parser.add_option("--priority", action="store_true",
                      help="show package priority")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts, ctrl):
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
    for name in opts.whoprovides:
        if '=' in name:
            name, version = name.split('=')
        else:
            version = None
        if isre(name):
            p = re.compile(name)
            for prv in cache.getProvides():
                if p.match(prv.name):
                    whoprovides.append(Provides(prv.name, version))
        else:
            whoprovides.append(Provides(name, version))
    whorequires = []
    for name in opts.whorequires:
        if '=' in name:
            name, version = name.split('=')
        else:
            version = None
        if isre(name):
            p = re.compile(name)
            for req in cache.getRequires():
                if p.match(req.name):
                    whorequires.append(Provides(req.name, version))
        else:
            whorequires.append(Provides(name, version))
    whoupgrades = []
    for name in opts.whoupgrades:
        if '=' in name:
            name, version = name.split('=')
        else:
            version = None
        if isre(name):
            p = re.compile(name)
            for upg in cache.getUpgrades():
                if p.match(upg.name):
                    whoupgrades.append(Provides(upg.name, version))
        else:
            whoupgrades.append(Provides(name, version))
    whoconflicts = []
    for name in opts.whoconflicts:
        if '=' in name:
            name, version = name.split('=')
        else:
            version = None
        if isre(name):
            p = re.compile(name)
            for cnf in cache.getConflicts():
                if p.match(cnf.name):
                    whoconflicts.append(Provides(cnf.name, version))
        else:
            whoconflicts.append(Provides(name, version))

    if whoprovides or whorequires or whoupgrades or whoconflicts:
        newpackages = []
        for whoprv in whoprovides:
            for prv in cache.getProvides(whoprv.name):
                if not whoprv.version or prv.name == prv.version:
                    for pkg in prv.packages:
                        if pkg in packages:
                            newpackages.append(pkg)
        for whoreq in whorequires:
            for req in cache.getRequires(whoreq.name):
                if req.matches(whoreq):
                    for pkg in req.packages:
                        if pkg in packages:
                            newpackages.append(pkg)
        for whoupg in whoupgrades:
            for upg in cache.getUpgrades(whoupg.name):
                if upg.matches(whoupg):
                    for pkg in upg.packages:
                        if pkg in packages:
                            newpackages.append(pkg)
        for whocnf in whoconflicts:
            for cnf in cache.getConflicts(whocnf.name):
                if cnf.matches(whocnf):
                    for pkg in cnf.packages:
                        if pkg in packages:
                            newpackages.append(pkg)
        packages = newpackages

    packages.sort()
    for pkg in packages:
        if opts.priority:
            print pkg, "{%s}" % pkg.getPriority()
        else:
            print pkg
        if pkg.provides and (opts.provides or whoprovides):
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
                if opts.requiredby and prv.requiredby:
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
                                print "       ", "%s (%s)" % (reqpkg, prv)
                if opts.upgradedby and prv.upgradedby:
                    print "      Upgraded By:"
                    for upg in prv.upgradedby:
                        upg.packages.sort()
                        for upgpkg in upg.packages:
                            if opts.installed and not upgpkg.installed:
                                continue
                            print "       ", "%s (%s)" % (upgpkg, prv)
                if opts.conflictedby and prv.conflictedby:
                    print "      Conflicted By:"
                    for cnf in prv.conflictedby:
                        cnf.packages.sort()
                        for cnfpkg in cnf.packages:
                            if opts.installed and not cnfpkg.installed:
                                continue
                            print "       ", "%s (%s)" % (cnfpkg, prv)
        if pkg.requires and (opts.requires or opts.prerequires or whorequires):
            pkg.requires.sort()
            first = True
            for req in pkg.requires:
                if opts.prerequires and not isinstance(req, PreRequires):
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
                if opts.providedby and req.providedby:
                    print "      Provided By:"
                    for prv in req.providedby:
                        prv.packages.sort()
                        for prvpkg in prv.packages:
                            if opts.installed and not prvpkg.installed:
                                continue
                            print "       ", "%s (%s)" % (prvpkg, prv)
        if pkg.upgrades and (opts.upgrades or whoupgrades):
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
                if opts.providedby and upg.providedby:
                    print "      Provided By:"
                    for prv in upg.providedby:
                        prv.packages.sort()
                        for prvpkg in prv.packages:
                            if opts.installed and not prvpkg.installed:
                                continue
                            print "       ", "%s (%s)" % (prvpkg, prv)
        if pkg.conflicts and (opts.conflicts or whoconflicts):
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
                if opts.providedby and cnf.providedby:
                    print "      Provided By:"
                    for prv in cnf.providedby:
                        prv.packages.sort()
                        for prvpkg in prv.packages:
                            if opts.installed and not prvpkg.installed:
                                continue
                            print "       ", "%s (%s)" % (prvpkg, prv)

# vim:ts=4:sw=4:et

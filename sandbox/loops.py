import sys
sys.argv = ["./cpm.py", "test"]
execfile('./cpm.py')

import sets
from cpm.cache import Package

def forwardRequires(pkg, set):
    for req in pkg.requires:
        if req not in set:
            set.add(req)
            for prv in req.providedby:
                if prv not in set:
                    set.add(prv)
                    for prvpkg in prv.packages:
                        if prvpkg not in set:
                            set.add(prvpkg)
                            forwardRequires(prvpkg, set)

def backwardRequires(pkg, set):
    for prv in pkg.provides:
        if prv not in set:
            set.add(prv)
            for req in prv.requiredby:
                if req not in set:
                    set.add(req)
                    for reqpkg in req.packages:
                        if reqpkg not in set:
                            set.add(reqpkg)
                            backwardRequires(reqpkg, set)

def findPkgLoops(pkg):
    fwd = sets.Set([pkg])
    forwardRequires(pkg, fwd)
    bwd = sets.Set([pkg])
    backwardRequires(pkg, bwd)
    return fwd.intersection(bwd)

def findLoops():
    pkgs = cache.getPackages()
    doneset = sets.Set()
    loops = []
    for pkg in pkgs:
        if pkg not in doneset:
            set = findPkgLoops(pkg)
            if len([x for x in set if isinstance(x, Package)]) > 1:
                loops.append(set)
            doneset.update(set)
    return loops

def dumpLoops():
    loops = findLoops()
    shown = sets.Set()
    n = 0
    for set in loops:
        n += 1
        file = open("loop%02d.dot" % n, "w")
        file.write("digraph Loops {\n")
        for pkg in [x for x in set if isinstance(x, Package)]:
            if pkg not in shown:
                shown.add(pkg)
                file.write('    "%s" [ shape = box ];\n' % pkg)
            for req in pkg.requires:
                if req not in set:
                    continue
                if (pkg, req) not in shown:
                    shown.add((pkg, req))
                    file.write('    "%s" -> "Requires: %s";\n' % (pkg, req))
                for prv in req.providedby:
                    if prv not in set:
                        continue
                    if (req, prv) not in shown:
                        shown.add((req, prv))
                        file.write('    "Requires: %s" -> "Provides: %s";\n' % (req, prv))
                    for prvpkg in prv.packages:
                        if prvpkg not in set:
                            continue
                        if (prv, prvpkg) not in shown:
                            shown.add((prv, prvpkg))
                            file.write('    "Provides: %s" -> "%s";\n' % (prv, prvpkg))
        file.write("}\n")

dumpLoops()
        

# vim:ts=4:sw=4:et

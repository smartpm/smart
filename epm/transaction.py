from epm.sorter import UpgradeSorter, ObsoletesSorter

(
OPER_INSTALL,
OPER_REMOVE,
) = range(1,3)

(
REASON_REQUESTED,
REASON_REQUIRES,
REASON_OBSOLETES,
REASON_CONFLICTS,
) = range(1,5)

class Max:
    def __cmp__(self, other):
        return 1
    def __int__(self):
        return 123456789

FAILED = 1000000000

MAX = Max()

class Policy:
    def __init__(self):
        self._locked = {}

    def getLocked(self, pkg):
        return pkg in self._locked

    def setLocked(self, pkg, flag):
        if flag:
            if pkg in self._locked:
                del self._locked[pkg]
        else:
            self._locked[pkg] = True

    def getLockedSet(self):
        return self._locked

    def getWeight(self, trans):
        return 0

    def getStartingWeight(self, trans):
        return MAX

class PolicyInstall(Policy):
    """Give precedence to keeping functionality in the system."""

    def getWeight(self, trans):
        weight = 0
        for pkg in trans.operation:
            op, reason, pkg1, pkg2 = trans.operation[pkg]
            if reason == REASON_REQUESTED:
                continue
            if op == OPER_REMOVE:
                if reason == REASON_OBSOLETES:
                    weight += 5
                else:
                    weight += 20
            elif op == OPER_INSTALL:
                weight += 1
        return weight

class PolicyRemove(Policy):
    """Give precedence to the choice with less changes."""

    def getWeight(self, trans):
        weight = 0
        for pkg in trans.operation:
            op, reason, pkg1, pkg2 = trans.operation[pkg]
            if reason == REASON_REQUESTED:
                continue
            if op == OPER_REMOVE:
                weight += 1
            elif op == OPER_INSTALL:
                weight += 5
        return weight

class PolicyGlobalUpgrade(Policy):
    """Give precedence to the choice with more upgrades and smaller impact."""

    def getWeight(self, trans):
        weight = 0
        for pkg in trans.operation:
            op, reason, pkg1, pkg2 = trans.operation[pkg]
            if op == OPER_REMOVE:
                if reason == REASON_OBSOLETES:
                    weight -= 5
                elif reason != REASON_REQUESTED:
                    weight += 20 
            elif op == OPER_INSTALL:
                if reason == REASON_REQUESTED:
                    weight -= 5
                else:
                    weight += 1
        return weight

    def getStartingWeight(self, trans):
        return self.getWeight(trans)

def recursiveRequiredBy(pkg, set):
    set[pkg] = True
    for prv in pkg.provides:
        for req in prv.requiredby:
            for reqpkg in req.packages:
                if reqpkg not in set:
                    recursiveRequiredBy(reqpkg, set)

def recursiveObsoletes(pkg, set):
    set[pkg] = True
    for obs in pkg.obsoletes:
        for prv in obs.providedby:
            for prvpkg in prv.packages:
                if prvpkg not in set:
                    recursiveObsoletes(prvpkg, set)

class Failed(Exception): pass

class Transaction:
    def __init__(self, cache, policy=None):
        self.cache = cache
        self.policy = policy
        self.backtrack = []
        self.operation = {}
        self.locked = {}
        self.queue = []

    def getLocked(self):
        return self.locked

    def getCache(self):
        return self.cache

    def getPolicy(self):
        return self.policy

    def setPolicy(self, policy):
        self.policy = policy

    def getState(self):
        return (self.operation.copy(), self.locked.copy(), self.queue[:])

    def setState(self, state):
        self.operation.clear()
        self.operation.update(state[0])
        self.locked.clear()
        self.locked.update(state[1])
        self.queue[:] = state[2]

    def getWeight(self):
        return self.policy.getWeight(self)

    def getInstalled(self, pkg):
        elem = self.operation.get(pkg)
        op = elem and elem[0] or None
        return op == OPER_INSTALL or pkg.installed and op != OPER_REMOVE

    def getOperations(self):
        self.cleanup()
        install = {}
        remove = {}
        for pkg in self.operation:
            op, reason, pkg1, pkg2 = self.operation[pkg]
            if op == OPER_INSTALL:
                install[pkg] = True
            else:
                remove[pkg] = True
        return install, remove

    def cleanup(self):
        for pkg in self.operation:
            op, reason, pkg1, pkg2 = self.operation[pkg]
            if (op == OPER_INSTALL) == pkg.installed:
                del self.operation[pkg]

    def restate(self):
        """
        After running this method, previously requested changes may be
        modified to fix relations.
        """
        self.locked.clear()
        self.queue.clear()

    def fixup(self, pkg):
        self.locked[pkg] = True
        self.queue.append((pkg, len(self.backtrack)))

    def toggle(self, pkg, fixup=True):
        self.locked[pkg] = True
        opmap = self.operation
        if pkg in opmap:
            op = opmap[pkg][0] == OPER_INSTALL and OPER_REMOVE or OPER_INSTALL
        else:
            op = pkg.installed and OPER_REMOVE or OPER_INSTALL
        if (op == OPER_INSTALL) != pkg.installed:
            self.operation[pkg] = (op, REASON_REQUESTED, None, None)
        elif pkg in self.operation:
            del self.operation[pkg]
        if fixup:
            self.fixup(pkg)

    def install(self, pkg, fixup=True):
        self.operation[pkg] = (OPER_INSTALL, REASON_REQUESTED, None, None)
        if fixup:
            self.fixup(pkg)

    def remove(self, pkg, fixup=True):
        self.operation[pkg] = (OPER_REMOVE, REASON_REQUESTED, None, None)

        if fixup:
            self.fixup(pkg)

            # We don't want to upgrade/downgrade that package.
            for obs in pkg.obsoletes:
                for prv in obs.providedby:
                    for prvpkg in prv.packages:
                        self.locked[prvpkg] = True
            for prv in pkg.provides:
                for obs in prv.obsoletedby:
                    for obspkg in obs.packages:
                        self.locked[obspkg] = True

    def upgrade(self, pkg, fixup=True):
        obspkgs = {}
        for prv in pkg.provides:
            for obs in prv.obsoletedby:
                for obspkg in obs.packages:
                    obspkgs[obspkg] = True
        if obspkgs:
            obspkgs = obspkgs.keys()
            ObsoletesSorter(obspkgs).sort()
            self.install(obspkgs[0], fixup=fixup)

    def run(self):
        loopctrl = {}

        locked = self.locked
        opmap = self.operation
        queue = self.queue
        isinst = self.getInstalled
        bt = self.backtrack

        beststate = self.getState()
        bestweight = self.policy.getStartingWeight(self)

        getweight = self.policy.getWeight
        locked.update(self.policy.getLockedSet())
        
        i = 0
        ilim = 1000

        while True:

            try:
            
                while True:

                    if not queue:
                        break

                    pkg, btlen = queue.pop(0)

                    if isinst(pkg):

                        # Remove packages obsoleted by this one.
                        for obs in pkg.obsoletes:
                            for prv in obs.providedby:
                                for prvpkg in prv.packages:
                                    if not isinst(prvpkg):
                                        continue
                                    if prvpkg in locked:
                                        raise Failed
                                    self._remove(prvpkg,
                                                 REASON_OBSOLETES,
                                                 pkg, prvpkg)

                        # Remove packages obsoleting this one.
                        for prv in pkg.provides:
                            for obs in prv.obsoletedby:
                                for obspkg in obs.packages:
                                    if not isinst(obspkg):
                                        continue
                                    if obspkg in locked:
                                        raise Failed
                                    self._remove(obspkg,
                                                 REASON_OBSOLETES,
                                                 obspkg, pkg)

                        # Remove packages conflicted by this one.
                        for cnf in pkg.conflicts:
                            for prv in cnf.providedby:
                                for prvpkg in prv.packages:
                                    if not isinst(prvpkg):
                                        continue
                                    if prvpkg in locked:
                                        raise Failed
                                    self._remove(prvpkg,
                                                 REASON_CONFLICTS,
                                                 pkg, prvpkg)

                        # Remove packages conflicting with this one.
                        for prv in pkg.provides:
                            for cnf in prv.conflictedby:
                                for cnfpkg in cnf.packages:
                                    if not isinst(cnfpkg):
                                        continue
                                    if cnfpkg in locked:
                                        raise Failed
                                    self._remove(cnfpkg,
                                                 REASON_CONFLICTS,
                                                 cnfpkg, pkg)

                        # Install packages required by this one.
                        for req in pkg.requires:

                            # Check if someone is already providing it.
                            prvpkgs = {}
                            found = False
                            for prv in req.providedby:
                                for prvpkg in prv.packages:
                                    if isinst(prvpkg):
                                        found = True
                                        break
                                    if prvpkg not in locked:
                                        prvpkgs[prvpkg] = True
                                else:
                                    continue
                                break
                            if found:
                                # Someone is already providing it. Good.
                                continue

                            # No one is currently providing it. Do something.
                            prvpkgs = prvpkgs.keys()
                            if not prvpkgs:
                                # No packages provide it at all. Give up.
                                raise Failed
                            if len(prvpkgs) > 1:
                                # More than one package provide it.
                                # Register alternatives.
                                prvpkgs.sort()
                                for prvpkg in prvpkgs[1:]:
                                    bt.append((prvpkg,
                                               OPER_INSTALL,
                                               REASON_REQUIRES,
                                               pkg, prvpkg,
                                               self.getState()))
                            prvpkg = prvpkgs[0]
                            queue.append((prvpkg, len(bt)))
                            locked[prvpkg] = True
                            opmap[prvpkg] = (OPER_INSTALL,
                                             REASON_REQUIRES,
                                             pkg, prvpkgs[0])

                    else: # if op == OPER_REMOVE:

                        # Remove packages requiring this one.
                        for prv in pkg.provides:
                            for req in prv.requiredby:
                                # Check if someone installed is requiring it.
                                for reqpkg in req.packages:
                                    if isinst(reqpkg):
                                        break
                                else:
                                    # No one requires it, so it doesn't matter.
                                    continue

                                # Check if someone installed is still
                                # providing it.
                                prvpkgs = {}
                                found = False
                                for prv in req.providedby:
                                    for prvpkg in prv.packages:
                                        if prvpkg is pkg:
                                            continue
                                        if isinst(prvpkg):
                                            found = True
                                            break
                                        if prvpkg not in locked:
                                            prvpkgs[prvpkg] = True
                                    else:
                                        continue
                                    break
                                if found:
                                    # Someone is still providing it. Good.
                                    continue

                                # No one is providing it anymore. Try to install
                                # other providing packages as alternatives.
                                if prvpkgs:
                                    prvpkgs = prvpkgs.keys()
                                    prvpkgs.sort()
                                    for prvpkg in prvpkgs:
                                        bt.append((prvpkg,
                                                   OPER_INSTALL,
                                                   REASON_REQUIRES,
                                                   reqpkg, pkg,
                                                   self.getState()))

                                # Then, remove requiring packages.
                                for reqpkg in req.packages:
                                    if not isinst(reqpkg):
                                        continue
                                    if reqpkg in locked:
                                        raise Failed
                                    self._remove(reqpkg,
                                                 REASON_REQUIRES,
                                                 reqpkg, pkg)
            except Failed:
                del bt[btlen:]
                weight = getweight(self)+FAILED
                print "Failed!"
            else:
                print "Succeeded!"
                weight = getweight(self)

            # Queue is over. Consider alternatives.
            """
            print "Queue is over!"
            print "Current weight is %d.\n" % weight
            """
            if bt:
                i += 1
                if i == ilim:
                    print "Alternatives/Weight: %d/%d" % (len(bt), weight)
                print "Found %d alternative(s)." % len(bt)
                if weight < bestweight:
                    print "Replacing beststate (%d < %d)" % (weight, bestweight)
                    beststate = self.getState()
                    bestweight = weight
                pkg, op, reason, pkg1, pkg2, state = bt.pop()
                self.setState(state)
                locked[pkg] = True
                queue.append((pkg, len(bt)))
                opmap[pkg] = (op, reason, pkg1, pkg2)
                print "Checking", pkg, "with", op
                if i == ilim:
                    print "Starting weight: %d" % getweight(self)
                    i = 0
            else:
                print "Alternatives are over!"
                # Replace in case of same weight to give precedence to
                # the first processed alternative.
                if weight >= bestweight:
                    print "Replacing current state (%d <= %d)" % (bestweight, weight)
                    self.setState(beststate)
                elif beststate:
                    print "Current state is better than beststate (%d < %d)" % (weight, bestweight)
                for p in opmap:
                    o, r, p1, p2 = opmap[p]
                    if o == OPER_INSTALL:
                        print "I", p
                    else:
                        print "R", p
                break

    def _remove(self, pkg, reason, pkg1, pkg2):
        """
        Remove package including upgrade/downgrade as an alternative.
        """
        # Look for packages obsoleting the removed
        # package (upgrade) as an alternative.
        for prv in pkg.provides:
            for obs in prv.obsoletedby:
                for obspkg in obs.packages:
                    if obspkg in self.locked or self.getInstalled(obspkg):
                        continue
                    self.backtrack.append((obspkg,
                                           OPER_INSTALL,
                                           reason, pkg1, pkg2,
                                           self.getState()))
        # Look for packages obsoleted by the removed
        # package (downgrade) as an alternative.
        for obs in pkg.obsoletes:
            for prv in obs.providedby:
                for prvpkg in prv.packages:
                    if prvpkg in self.locked or self.getInstalled(prvpkg):
                        continue
                    self.backtrack.append((prvpkg,
                                           OPER_INSTALL,
                                           reason, pkg1, pkg2,
                                           self.getState()))

        # Finally, remove the package.
        self.locked[pkg] = True
        self.queue.append((pkg, len(self.backtrack)))
        self.operation[pkg] = (OPER_REMOVE, reason, pkg1, pkg2)

def upgradePackages(trans, pkgs):
    locked = trans.getLocked()
    isinst = trans.getInstalled

    # Find packages obsoleting given packages.
    upgpkgs = {}
    for pkg in pkgs:
        if isinst(pkg):
            for prv in pkg.provides:
                for obs in prv.obsoletedby:
                    for obspkg in obs.packages:
                        if (obspkg in locked or
                            obspkg in upgpkgs or
                            isinst(obspkg)):
                            continue
                        upgpkgs[obspkg] = True

    upgpkgs = upgpkgs.keys()
    print [str(x) for x in upgpkgs]
    #import sys
    #sys.exit(0)

    import time
    start = time.time()
    evaluateBestState(trans, upgpkgs)
    print time.time()-start

    """
    # Ordering is key.
    UpgradeSorter(upgpkgs).sort()

    print [str(x) for x in upgpkgs]
    
    beststate = trans.getState()
    bestweight = trans.getPolicy().getStartingWeight(trans)
    for pkg in upgpkgs:
        if pkg in locked:
            continue
        trans.install(pkg)
        trans.run()
        weight = trans.getWeight()
        if weight < bestweight:
            beststate = trans.getState()
            bestweight = weight
        else:
            trans.setState(beststate)

    print "Upgrade:"
    for pkg in trans.operation:
        o, r, p1, p2 = trans.operation[pkg]
        if o == OPER_INSTALL:
            print "I", pkg
        else:
            print "R", pkg
    """

def evaluateBestState(trans, pkgs):
    locked = trans.getLocked()
    isinst = trans.getInstalled
    trans.setPolicy(PolicyGlobalUpgrade())

    backtrack = []
    beststate = trans.getState()
    bestweight = trans.getPolicy().getStartingWeight(trans)
    i = 0
    lenpkgs = len(pkgs)
    n = 0
    while True:
        n += 1
        pkg = pkgs[i]
        if n % 8192 == 0:
            print n, [x[0] for x in backtrack]

        if pkg not in locked:
            # Try to change the state later.
            backtrack.append((i, trans.getState()))
            trans.fixup(pkg)

        i += 1
        if i == lenpkgs:
            trans.run()
            weight = trans.getWeight()
            if weight < bestweight:
                beststate = trans.getState()
                bestweight = weight
            if backtrack:
                i, state = backtrack.pop()
                trans.setState(state)
                trans.toggle(pkgs[i])
            else:
                break

    trans.setState(beststate)
    print "Best evaluated state (%d):" % trans.getWeight()
    trans.cleanup()
    for pkg in trans.operation:
        o, r, p1, p2 = trans.operation[pkg]
        if o == OPER_INSTALL:
            print "I", pkg
        else:
            print "R", pkg

    global TRANS, BESTSTATE
    TRANS = trans
    BESTSTATE = beststate
    BESTWEIGHT = bestweight

try:
    import psyco
except ImportError:
    pass
else:
    psyco.bind(Transaction)

# vim:ts=4:sw=4:et

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

FAILED = 100000000

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
            if reason != REASON_REQUESTED:
                weight += 1
        return weight

class PolicyGlobalUpgrade(Policy):
    """Give precedence to the choice with more upgrades and smaller impact."""

    def getWeight(self, trans):
        trans = self._trans
        weight = 0
        for pkg in trans.operation:
            op, reason, pkg1, pkg2 = trans.operation[pkg]
            if reason == REASON_REQUESTED:
                continue
            if op == OPER_REMOVE:
                if reason == REASON_OBSOLETES:
                    weight -= 5
                else:
                    weight += 20 
            elif op == OPER_INSTALL:
                weight += 1
        return weight

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
        return self.policy.getWeight()

    def getInstalled(self, pkg):
        elem = self.operation.get(pkg)
        op = elem and elem[0] or None
        return op == OPER_INSTALL or pkg.installed and op != OPER_REMOVE

    def restate(self):
        """
        After running this method, previously requested changes may be
        modified to fix relations.
        """
        self.locked.clear()

    def install(self, pkg):
        self.locked[pkg] = True
        if not self.getInstalled(pkg):
            self.operation[pkg] = (OPER_INSTALL, REASON_REQUESTED, None, None)
        self.queue.append((pkg, OPER_INSTALL, len(self.backtrack)))

    def remove(self, pkg):
        self.locked[pkg] = True
        self.operation[pkg] = (OPER_REMOVE, REASON_REQUESTED, None, None)
        self.queue.append((pkg, OPER_REMOVE, len(self.backtrack)))

        # We don't want to upgrade/downgrade that package.
        for obs in pkg.obsoletes:
            for prv in obs.providedby:
                for prvpkg in prv.packages:
                    self.locked[prvpkg] = True
        for prv in pkg.provides:
            for obs in prv.obsoletedby:
                for obspkg in obs.packages:
                    self.locked[obspkg] = True

    def upgrade(self, pkg):
        obspkgs = {}
        for prv in pkg.provides:
            for obs in prv.obsoletedby:
                for obspkg in obs.packages:
                    obspkgs[obspkg] = True
        if obspkgs:
            obspkgs = obspkgs.keys()
            ObsoletesSorter(obspkgs).sort()
            self.install(obspkgs[0])

    def run(self):
        loopctrl = {}

        locked = self.locked
        opmap = self.operation
        queue = self.queue
        isinst = self.getInstalled
        bt = self.backtrack

        beststate = None
        bestweight = "MAX"

        getweight = self.policy.getWeight
        locked.update(self.policy.getLockedSet())
        
        i = 0
        ilim = 1000

        while True:

            try:
            
                while True:

                    if not queue:
                        break

                    pkg, op, btlen = queue.pop(0)

                    if op == OPER_INSTALL:

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
                            queue.append((prvpkg, OPER_INSTALL, len(bt)))
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
            else:
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
                #print "Found %d alternative(s)." % len(bt)
                if weight < bestweight:
                    print "Replacing beststate (%d < %s)" % (weight, str(bestweight))
                    beststate = self.getState()
                    bestweight = weight
                pkg, op, reason, pkg1, pkg2, state = bt.pop()
                self.setState(state)
                locked[pkg] = True
                queue.append((pkg, op, len(bt)))
                opmap[pkg] = (op, reason, pkg1, pkg2)
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
        self.queue.append((pkg, OPER_REMOVE, len(self.backtrack)))
        self.operation[pkg] = (OPER_REMOVE, reason, pkg1, pkg2)

def upgradePackages(self, trans, pkgs):
    locked = trans.getLocked()
    isinst = trans.getInstalled

    # Find packages obsoleting given packages.
    upgpkgs = {}
    for pkg in pkgs:
        if isinst(pkg):
            for prv in pkg.provides:
                for obs in prv.obsoletedby:
                    for obspkg in obs.packages:
                        if obspkg in locked or obspkg in upgpkgs:
                            continue
                        upgpkgs[obspkg] = True

    upgpkgs = upgpkgs.keys()

    # Ordering is key.
    UpgradeSorter(upgpkgs).sort()

    print [str(x) for x in upgpkgs]
    import sys
    sys.exit(0)
    
    beststate = trans.getState()
    bestweight = trans.getWeight()
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

    print "Global upgrade:"
    for pkg in trans.operation:
        o, r, p1, p2 = trans.operation[pkg]
        if o == OPER_INSTALL:
            print "I", pkg
        else:
            print "R", pkg

try:
    import psyco
except ImportError:
    pass
else:
    psyco.bind(Transaction)

# vim:ts=4:sw=4:et

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
    def __init__(self, trans):
        self._trans = trans

    def getWeight(self):
        return 0

class PolicyInstall(Policy):
    """Give precedence to keeping functionality in the system."""

    def getWeight(self):
        trans = self._trans
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

    def getWeight(self):
        trans = self._trans
        weight = 0
        for pkg in trans.operation:
            op, reason, pkg1, pkg2 = trans.operation[pkg]
            if reason != REASON_REQUESTED:
                weight += 1
        return weight

class PolicyGlobalUpgrade(Policy):
    """Give precedence to the choice with more upgrades and smaller impact."""

    def getWeight(self):
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

class Failed(Exception): pass

class Transaction:
    def __init__(self, cache, policy):
        self.cache = cache
        self.policy = policy(self)
        self.backtrack = []
        self.operation = {}
        self.touched = {}
        self.queue = []

    def getState(self):
        # Operation must be the first one, since we use state[0] in run().
        return (self.operation.copy(), self.touched.copy())

    def setState(self, state):
        self.operation.clear()
        self.operation.update(state[0])
        self.touched.clear()
        self.touched.update(state[1])

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
        self.touched.clear()

    def install(self, pkg):
        self.touched[pkg] = True
        if not self.getInstalled(pkg):
            self.operation[pkg] = (OPER_INSTALL, REASON_REQUESTED, None, None)
        self.queue.append((pkg, OPER_INSTALL))

    def remove(self, pkg):
        self.touched[pkg] = True
        self.operation[pkg] = (OPER_REMOVE, REASON_REQUESTED, None, None)
        self.queue.append((pkg, OPER_REMOVE))

        # We don't want to upgrade/downgrade that package.
        for obs in pkg.obsoletes:
            for prv in obs.providedby:
                for prvpkg in prv.packages:
                    if obs.pkgname and obs.pkgname != prvpkg.name:
                        continue
                    self.touched[prvpkg] = True
        for prv in pkg.provides:
            for obs in prv.obsoletedby:
                if obs.pkgname and obs.pkgname != pkg.name:
                    continue
                for obspkg in obs.packages:
                    self.touched[obspkg] = True

    def upgrade(self, pkg):
        obspkgs = [obspkg for prv in pkg.provides
                          for obs in prv.obsoletedby
                          for obspkg in obs.packages
                          if (not obs.pkgname or
                              obs.pkgname == pkg.name)]
        obspkgs.sort()
        self.install(obspkgs[-1])

    def globalUpgrade(self):
        cache = self.cache
        touched = self.touched

        isinst = self.getInstalled

        upgset = {}

        # Find multiple levels of packages obsoleting installed packages.
        queue = cache.getPackages()
        while queue:
            pkg = queue.pop(0)
            if isinst(pkg):
                for prv in pkg.provides:
                    for obs in prv.obsoletedby:
                        if obs.pkgname and obs.pkgname != pkg.name:
                            continue
                        for obspkg in obs.packages:
                            if obspkg in touched:
                                continue
                            if obspkg not in upgset:
                                print "%s obsoletes %s" % (obspkg, pkg)
                                upgset[obspkg] = True
                                queue.append(obspkg)

    def run(self):
        loopctrl = {}

        touched = self.touched
        opmap = self.operation
        queue = self.queue
        isinst = self.getInstalled
        backtrack = self.backtrack

        beststate = None
        bestweight = "MAX"

        getweight = self.policy.getWeight
        
        i = 0
        ilim = 1000

        while True:

            failed = None

            try:
            
                while True:

                    if not queue:
                        break

                    pkg, op = queue.pop(0)

                    # If this package fails in some point, all alternatives
                    # introduced from now on will fail as well. Thusly,
                    # we save the backtrack state here, and restore it
                    # on failures.
                    savedbt = backtrack[:]

                    if op == OPER_INSTALL:

                        # Remove packages obsoleted by this one.
                        for obs in pkg.obsoletes:
                            for prv in obs.providedby:
                                for prvpkg in prv.packages:
                                    if (obs.pkgname and
                                        obs.pkgname != prvpkg.name):
                                        continue
                                    if not isinst(prvpkg):
                                        continue
                                    if prvpkg in touched:
                                        failed = prv
                                        raise Failed
                                    self._remove(prvpkg,
                                                 REASON_OBSOLETES,
                                                 pkg, prvpkg)

                        # Remove packages obsoleting this one.
                        for prv in pkg.provides:
                            for obs in prv.obsoletedby:
                                for obspkg in obs.packages:
                                    if (obs.pkgname and
                                        obs.pkgname != pkg.name):
                                        continue
                                    if not isinst(obspkg):
                                        continue
                                    if obspkg in touched:
                                        failed = obs
                                        raise Failed
                                    self._remove(obspkg,
                                                 REASON_OBSOLETES,
                                                 obspkg, pkg)

                        # Remove packages conflicted by this one.
                        for cnf in pkg.conflicts:
                            for prv in cnf.providedby:
                                for prvpkg in prv.packages:
                                    if (cnf.pkgname and
                                        cnf.pkgname != prvpkg.name):
                                        continue
                                    if not isinst(prvpkg):
                                        continue
                                    if prvpkg in touched:
                                        failed = prv
                                        raise Failed
                                    self._remove(prvpkg,
                                                 REASON_CONFLICTS,
                                                 pkg, prvpkg)

                        # Remove packages conflicting with this one.
                        for prv in pkg.provides:
                            for cnf in prv.conflictedby:
                                for cnfpkg in cnf.packages:
                                    if (cnf.pkgname and
                                        cnf.pkgname != pkg.name):
                                        continue
                                    if not isinst(cnfpkg):
                                        continue
                                    if cnfpkg in touched:
                                        failed = cnf
                                        raise Failed
                                    self._remove(cnfpkg,
                                                 REASON_CONFLICTS,
                                                 cnfpkg, pkg)

                        # Install packages required by this one.
                        for req in pkg.requires:
                            # Check if someone is already providing it.
                            prvpkgs = [prvpkg for prv in req.providedby
                                              for prvpkg in prv.packages
                                              if (not req.pkgname or
                                                  req.pkgname == prvpkg.name)]
                            found = False
                            for prvpkg in prvpkgs:
                                if isinst(prvpkg):
                                    found = True
                                    break
                            if found:
                                # Someone is already providing it. Good.
                                continue

                            # No one is currently providing it. Do something.
                            prvpkgs = [prvpkg for prvpkg in prvpkgs
                                               if prvpkg not in touched]
                            if not prvpkgs:
                                # No packages provide it at all. Give up.
                                failed = req
                                raise Failed
                            if len(prvpkgs) > 1:
                                # More than one package provide it.
                                # Register alternatives.
                                prvpkgs.sort()
                                for prvpkg in prvpkgs[1:]:
                                    if prvpkg in touched or isinst(prvpkg):
                                        continue
                                    backtrack.append((prvpkg,
                                                      OPER_INSTALL,
                                                      REASON_REQUIRES,
                                                      pkg, prvpkg,
                                                      self.getState()))
                            prvpkg = prvpkgs[0]
                            queue.append((prvpkg, OPER_INSTALL))
                            touched[prvpkg] = True
                            opmap[prvpkg] = (OPER_INSTALL,
                                             REASON_REQUIRES,
                                             pkg, prvpkgs[0])

                    else: # if OPER_REMOVE

                        # Remove packages requiring this one.
                        for prv in pkg.provides:
                            for req in prv.requiredby:
                                if req.pkgname and req.pkgname != pkg.name:
                                    continue
                                # Check if someone installed is requiring it.
                                for reqpkg in req.packages:
                                    if isinst(reqpkg):
                                        break
                                else:
                                    # No one requires it, so it doesn't matter.
                                    continue

                                # Check if someone installed is still providing it.
                                prvpkgs = []
                                found = False
                                for prv in req.providedby:
                                    for prvpkg in prv.packages:
                                        if isinst(prvpkg):
                                            found = True
                                            break
                                        prvpkgs.append(prvpkg)
                                    else:
                                        continue
                                    break
                                if found:
                                    # Someone is still providing it. Good.
                                    continue

                                # No one is providing it anymore. Try to install
                                # other providing packages as alternatives.
                                if prvpkgs:
                                    prvpkgs.sort()
                                    for prvpkg in prvpkgs:
                                        if prvpkg in touched:
                                            continue
                                        backtrack.append((prvpkg,
                                                          OPER_INSTALL,
                                                          REASON_REQUIRES,
                                                          reqpkg, pkg,
                                                          self.getState()))

                                # Then, remove requiring packages.
                                for reqpkg in req.packages:
                                    if not isinst(reqpkg):
                                        continue
                                    if reqpkg in touched:
                                        failed = req
                                        raise Failed
                                    self._remove(reqpkg,
                                                 REASON_REQUIRES,
                                                 reqpkg, pkg)
            except Failed:
                backtrack[:] = savedbt

            # Queue is over. Consider alternatives.
            """
            print "Queue is over!"
            print "Current weight is %d.\n" % self.getWeight()
            """
            weight = getweight()
            if failed:
                weight += FAILED
            if backtrack:
                i += 1
                if i == ilim:
                    print "Alternatives/Weight: %d/%d" % (len(backtrack), weight)
                #print "Found %d alternative(s)." % len(backtrack)
                if weight < bestweight:
                    print "Replacing beststate (%d < %s)" % (weight, str(bestweight))
                    beststate = self.getState()
                    bestweight = weight
                while backtrack:
                    pkg, op, reason, pkg1, pkg2, state = backtrack.pop()
                    self.setState(state)
                    opmap[pkg] = (op, reason, pkg1, pkg2)
                    break
                    #if getweight() < bestweight:
                    #    break
                else:
                    break
                self.queue.append((pkg, op))
                touched[pkg] = True
                if i == ilim:
                    print "Starting weight: %d" % getweight()
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
                if obs.pkgname and obs.pkgname != pkg.name:
                    continue
                for obspkg in obs.packages:
                    if obspkg in self.touched or self.getInstalled(obspkg):
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
                    if obs.pkgname and obs.pkgname != prvpkg.name:
                        continue
                    if prvpkg in self.touched or self.getInstalled(prvpkg):
                        continue
                    self.backtrack.append((prvpkg,
                                           OPER_INSTALL,
                                           reason, pkg1, pkg2,
                                           self.getState()))

        # Finally, remove the package.
        self.queue.append((pkg, OPER_REMOVE))
        self.touched[pkg] = True
        self.operation[pkg] = (OPER_REMOVE, reason, pkg1, pkg2)

try:
    import psyco
except ImportError:
    pass
else:
    psyco.bind(Transaction)

# vim:ts=4:sw=4:et

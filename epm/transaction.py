from epm.sorter import UpgradeSorter, ObsoletesSorter
from epm import Error

INSTALL = True
REMOVE  = False

class ChangeSet:
    def __init__(self, state=None):
        if state:
            if hasattr(state, "_opmap"):
                self._opmap = state._opmap.copy()
            else:
                self._opmap = state.copy()
        else:
            self._opmap = {}

    def getSet(self):
        return self._opmap

    def setInstall(self, pkg):
        if pkg.installed:
            if pkg in self._opmap:
                del self._opmap[pkg]
        else:
            self._opmap[pkg] = True

    def getInstall(self, pkg):
        return self._opmap.get(pkg) is INSTALL

    def setRemove(self, pkg):
        if not pkg.installed:
            if pkg in self._opmap:
                del self._opmap[pkg]
        else:
            self._opmap[pkg] = False

    def getRemove(self, pkg):
        return self._opmap.get(pkg) is REMOVE

    def isInstalled(self, pkg):
        op = self._opmap.get(pkg)
        return op is INSTALL or pkg.installed and not op is REMOVE

    def getState(self):
        return self._opmap.copy()

    def setState(self, state):
        if hasattr(state, "_opmap"):
            state = state._opmap
        self._opmap.clear()
        self._opmap.update(state)
        return self

    def copy(self):
        return ChangeSet(self)
    
    def __str__(self):
        l = []
        opmap = self._opmap
        for pkg in self._opmap:
            if opmap[pkg]:
                l.append("I %s\n" % pkg)
            else:
                l.append("R %s\n" % pkg)
        return "".join(l)

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

    def getWeight(self, changeset):
        return 0

class PolicyInstall(Policy):
    """Give precedence to keeping functionality in the system."""

    def getWeight(self, changeset):
        weight = 0
        set = changeset.getSet()
        for pkg in set:
            op = set[pkg]
            if op is REMOVE:
                # Check if any obsoleting package is being installed
                obsoleted = False
                for prv in pkg.provides:
                    for obs in prv.obsoletedby:
                        for obspkg in obs.packages:
                            if set.get(obspkg) is INSTALL:
                                obsoleted = True
                                break
                        else:
                            continue
                        break
                    else:
                        continue
                    break
                if obsoleted:
                    weight += 5
                else:
                    weight += 20
            elif op is INSTALL:
                weight += 1
        return weight

class PolicyRemove(Policy):
    """Give precedence to the choice with less changes."""

    def getWeight(self, changeset):
        weight = 0
        set = changeset.getSet()
        for pkg in set:
            if set[pkg] is REMOVE:
                weight += 1
            else:
                weight += 5
        return weight

class PolicyUpgrade(Policy):
    """Give precedence to the choice with more upgrades and smaller impact."""

    def getWeight(self, changeset):
        weight = 0
        weight = 0
        set = changeset.getSet()
        # Compute obsoleting/obsoleted packages
        obsoleting = {}
        obsoleted = {}
        for pkg in set:
            for prv in pkg.provides:
                for obs in prv.obsoletedby:
                    for obspkg in obs.packages:
                        if set.get(obspkg) is INSTALL:
                            obsoleted[pkg] = True
                            obsoleting[obspkg] = True
        for pkg in set:
            op = set[pkg]
            if op is REMOVE:
                if pkg not in obsoleted:
                    weight += 20 
            elif op is INSTALL:
                if pkg in obsoleting:
                    weight -= 5
                else:
                    weight += 1
        return weight

class Failed(Error): pass

class Transaction:
    def __init__(self, cache, policy=None, changeset=None):
        self._cache = cache
        self._policy = policy
        self._changeset = changeset or ChangeSet()

    def getCache(self):
        return self._cache

    def getPolicy(self):
        return self._policy

    def setPolicy(self, policy):
        self._policy = policy

    def getWeight(self):
        return self._policy.getWeight(self._changeset)

    def getChangeSet(self):
        return self._changeset

    def setChangeSet(self, changeset):
        self._changeset = changeset

    def getState(self):
        return self._changeset.getState()

    def setState(self, state):
        self._changeset.setState(state)

    def isInstalled(self, pkg):
        return self._changeset.isInstalled(pkg)

    def __str__(self):
        return str(self._changeset)

    def _remove(self, pkg, changeset, locked):
        getweight = self._policy.getWeight
        alternatives = []
        # Check if any upgrade would get rid of the problem.
        for obs in pkg.obsoletes:
            for prv in obs.providedby:
                for prvpkg in prv.packages:
                    if prvpkg not in locked:
                        cs = changeset.copy()
                        try:
                            self.install(prvpkg, cs, locked)
                        except Failed:
                            pass
                        else:
                            alternatives.append((getweight(cs), cs))
        # Check if any downgrade would get rid of the problem.
        for prv in pkg.provides:
            for obs in prv.obsoletedby:
                for obspkg in obs.packages:
                    if obspkg not in locked:
                        cs = changeset.copy()
                        try:
                            self.install(obspkg, cs, locked)
                        except Failed:
                            pass
                        else:
                            alternatives.append((getweight(cs), cs))
        cs = changeset.copy()
        try:
            self.remove(pkg, cs, locked)
        except Failed:
            if not alternatives:
                raise
        else:
            alternatives.append((getweight(cs), cs))
        alternatives.sort()
        changeset.setState(alternatives[0][1])

    def install(self, pkg, changeset=None, locked=None):
        if not locked:
            locked = self._policy.getLockedSet().copy()
        else:
            locked = locked.copy()
        if pkg in locked:
            raise Failed, "can't install %s: it's locked" % pkg
        locked[pkg] = True
        if not changeset:
            changeset = self._changeset
        changeset.setInstall(pkg)
        isinst = changeset.isInstalled
        getweight = self._policy.getWeight

        # Remove packages obsoleted by this one.
        for obs in pkg.obsoletes:
            for prv in obs.providedby:
                for prvpkg in prv.packages:
                    if not isinst(prvpkg):
                        continue
                    if prvpkg in locked:
                        raise Failed, "can't install %s: obsoleted package " \
                                      "%s is locked" % (pkg, prvpkg)
                    # Since the package is being obsoleted, we
                    # don't check any alternatives.
                    self.remove(prvpkg, changeset, locked)

        # Remove packages obsoleting this one.
        for prv in pkg.provides:
            for obs in prv.obsoletedby:
                for obspkg in obs.packages:
                    if not isinst(obspkg):
                        continue
                    if obspkg in locked:
                        raise Failed, "can't install %s: it's obsoleted by " \
                                      "the locked package %s" % (pkg, obspkg)
                    self._remove(obspkg, changeset, locked)

        # Remove packages conflicted by this one.
        for cnf in pkg.conflicts:
            for prv in cnf.providedby:
                for prvpkg in prv.packages:
                    if not isinst(prvpkg):
                        continue
                    if prvpkg in locked:
                        raise Failed, "can't install %s: conflicted package " \
                                      "%s is locked" % (pkg, prvpkg)
                    self._remove(prvpkg, changeset, locked)

        # Remove packages conflicting with this one.
        for prv in pkg.provides:
            for cnf in prv.conflictedby:
                for cnfpkg in cnf.packages:
                    if not isinst(cnfpkg):
                        continue
                    if cnfpkg in locked:
                        raise Failed, "can't install %s: it's conflicted by " \
                                      "the locked package %s" % (pkg, cnfpkg)
                    self._remove(cnfpkg, changeset, locked)

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
                raise Failed, "can't install %s: no package provides %s" % \
                              (pkg, req)
            if len(prvpkgs) > 1:
                # More than one package provide it.
                alternatives = []
                failures = []
                for prvpkg in prvpkgs:
                    try:
                        cs = changeset.copy()
                        self.install(prvpkg, cs, locked)
                    except Failed, e:
                        failures.append(str(e))
                    else:
                        alternatives.append((getweight(cs), cs))
                if not alternatives:
                    raise Failed, "can't install %s: all packages providing " \
                                  "%s failed to install: %s" \
                                  (pkg, req,  "; ".join(failures))
                alternatives.sort()
                changeset.setState(alternatives[0][1])
            else:
                self.install(prvpkgs[0], changeset, locked)

    def remove(self, pkg, changeset=None, locked=None):
        if not locked:
            locked = self._policy.getLockedSet().copy()
        else:
            locked = locked.copy()
        if pkg in locked:
            raise Failed, "can't remove %s: it's locked" % pkg
        locked[pkg] = True
        if not changeset:
            changeset = self._changeset
        changeset.setRemove(pkg)
        isinst = changeset.isInstalled
        getweight = self._policy.getWeight

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

                # Check if someone installed is still providing it.
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

                # No one is providing it anymore. We'll have to do
                # something about it.

                alternatives = []
                failures = []
                lckd = locked.copy()
                
                # Try to install other providing packages.
                if prvpkgs:
                    for prvpkg in prvpkgs:
                        lckd[prvpkg] = True
                        try:
                            cs = changeset.copy()
                            self.install(prvpkg, cs, locked)
                        except Failed, e:
                            failures.append(str(e))
                        else:
                            alternatives.append((getweight(cs), cs))

                # Then, remove every requiring package, or
                # upgrade/downgrade them to something which
                # does not require this dependency (notice lckd).
                cs = changeset.copy()
                try:
                    for reqpkg in req.packages:
                        if reqpkg in locked or not isinst(reqpkg):
                            continue
                        self._remove(reqpkg, cs, lckd)
                except Failed:
                    failures.append(str(e))
                else:
                    alternatives.append((getweight(cs), cs))

                if not alternatives:
                    raise Failed, "can't remove %s: %s is being required " \
                                  "and all alternatives failed: %s" % \
                                  (pkg, prv, "; ".join(failures))

                alternatives.sort()
                changeset.setState(alternatives[0][1])

    def upgrade(self, pkgs, changeset=None):
        if not changeset:
            changeset = self._changeset
        isinst = changeset.isInstalled

        if type(pkgs) is not list:
            pkgs = [pkgs]

        # Find packages obsoleting given packages.
        upgpkgs = {}
        for pkg in pkgs:
            if isinst(pkg):
                for prv in pkg.provides:
                    for obs in prv.obsoletedby:
                        for obspkg in obs.packages:
                            if obspkg in upgpkgs or isinst(obspkg):
                                continue
                            upgpkgs[obspkg] = True

        self.evalBestState(upgpkgs.keys(), changeset, install=True, keep=True)

    def evalBestState(self, pkgs, changeset=None,
                      install=False, remove=False, keep=False, upgrade=False):
        if not changeset:
            changeset = self._changeset
        getweight = self._policy.getWeight

        if type(pkgs) is not list:
            pkgs = [pkgs]

        weight = getweight(changeset)
        state = changeset.getState()
        for pkg in pkgs:
            alternatives = []
            failures = []
            if keep:
                alternatives.append((weight, state))

            if install:
                try:
                    cs = changeset.copy()
                    self.install(pkg, cs)
                except Failed, e:
                    failures.append(str(e))
                else:
                    alternatives.append((getweight(cs), cs))

            if remove:
                try:
                    cs = changeset.copy()
                    self.remove(pkg, cs)
                except Failed, e:
                    failures.append(str(e))
                else:
                    alternatives.append((getweight(cs), cs))

            if upgrade:
                try:
                    cs = changeset.copy()
                    self.upgrade(pkg, cs)
                except Failed, e:
                    failures.append(str(e))
                else:
                    alternatives.append((getweight(cs), cs))

            if not alternatives:
                if not failures:
                    failures.append("wrong parameters")
                raise Failed, "no best state for %s: %s" % \
                              (pkg, "; ".join(failures))

            alternatives.sort()
            weight, state = alternatives[0]
            changeset.setState(state)
                
try:
    import psyco
except ImportError:
    pass
else:
    psyco.bind(Transaction)

# vim:ts=4:sw=4:et

from cpm.const import INSTALL, REMOVE
from cpm import *

class ChangeSet(object):
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
            self._opmap[pkg] = INSTALL

    def getInstall(self, pkg):
        return self._opmap.get(pkg) is INSTALL

    def setRemove(self, pkg):
        if not pkg.installed:
            if pkg in self._opmap:
                del self._opmap[pkg]
        else:
            self._opmap[pkg] = REMOVE

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

    def __nonzero__(self):
        return bool(self._opmap)
    
    def __str__(self):
        l = []
        opmap = self._opmap
        for pkg in self._opmap:
            if opmap[pkg]:
                l.append("I %s\n" % pkg)
            else:
                l.append("R %s\n" % pkg)
        return "".join(l)

class Policy(object):
    def __init__(self, cache):
        self._cache = cache
        self._locked = {}
        self._upgradelocked = {}
        self._downgradelocked = {}
        pkgflags = sysconf.get("package-flags")
        if pkgflags:
            lock = pkgflags.filter("lock", cache.getPackages())
            self._locked = dict.fromkeys(lock)
            lock = pkgflags.filter("upgrade-lock", cache.getPackages())
            self._upgradelocked = dict.fromkeys(lock)
            lock = pkgflags.filter("downgrade-lock", cache.getPackages())
            self._downgradelocked = dict.fromkeys(lock)

    def getLocked(self, pkg):
        return pkg in self._locked

    def getUpgradeLocked(self, pkg):
        return pkg in self._upgradelocked

    def getDowngradeLocked(self, pkg):
        return pkg in self._downgradelocked

    def setLocked(self, pkg, flag):
        if flag:
            self._locked[pkg] = True
        else:
            if pkg in self._locked:
                del self._locked[pkg]

    def setUpgradeLocked(self, pkg, flag):
        if flag:
            self._upgradelocked[pkg] = True
        else:
            if pkg in self._upgradelocked:
                del self._upgradelocked[pkg]

    def setDowngradeLocked(self, pkg, flag):
        if flag:
            self._downgradelocked[pkg] = True
        else:
            if pkg in self._downgradelocked:
                del self._downgradelocked[pkg]

    def getLockedSet(self):
        return self._locked

    def getUpgradeLockedSet(self):
        return self._upgradelocked

    def getDowngradeLockedSet(self):
        return self._upgradelocked

    def getWeight(self, changeset):
        return 0

class PolicyInstall(Policy):
    """Give precedence for keeping functionality in the system."""

    def getWeight(self, changeset):
        weight = 0
        set = changeset.getSet()
        # Compute upgrading/upgraded packages
        upgrading = {}
        upgraded = {}
        for pkg in set:
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if prvpkg.installed:
                            upgrading[pkg] = True
                            if set.get(prvpkg) is REMOVE:
                                upgraded[pkg] = True
        for pkg in set:
            op = set[pkg]
            if op is REMOVE:
                if pkg in upgraded:
                    # Upgrading a package that will be removed
                    # is better than upgrading a package that will
                    # stay in the system.
                    weight -= 1
                else:
                    weight += 20
            elif op is INSTALL:
                if pkg in upgrading:
                    weight += 2
                else:
                    weight += 3
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
        set = changeset.getSet()
        # Compute upgrading/upgraded packages
        upgrading = {}
        upgraded = {}
        for pkg in set:
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if prvpkg.installed:
                            # Check if another package has already upgraded
                            # this one. Two different packages upgrading the
                            # same package is not valuable.
                            if prvpkg not in upgraded:
                                upgrading[pkg] = True
                                if set.get(prvpkg) is REMOVE:
                                    upgraded[prvpkg] = True
        for pkg in set:
            op = set[pkg]
            if op is REMOVE:
                if pkg in upgraded:
                    # Upgrading a package that will be removed
                    # is better than upgrading a package that will
                    # stay in the system.
                    weight -= 1
                else:
                    weight += 20
            else:
                if pkg in upgrading:
                    weight -= 4
                else:
                    weight += 1
        return weight

class Failed(Error): pass

class Transaction(object):
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

    def getInstallList(self):
        set = self._changeset.getSet()
        return [pkg for pkg in set if set[pkg] is INSTALL]

    def getRemoveList(self):
        set = self._changeset.getSet()
        return [pkg for pkg in set if set[pkg] is REMOVE]

    def __nonzero__(self):
        return bool(self._changeset)

    def __str__(self):
        return str(self._changeset)

    def _remove(self, pkg, changeset, locked):
        getweight = self._policy.getWeight
        alternatives = []
        cs = changeset.copy()
        self.remove(pkg, cs, locked)
        alternatives.append((getweight(cs), cs))

        locked = locked.copy()
        locked[pkg] = True

        # Check if upgrading is possible.
        for upg in pkg.upgrades:
            for prv in upg.providedby:
                for prvpkg in prv.packages:
                    if prvpkg not in locked:
                        cs = changeset.copy()
                        try:
                            self.install(prvpkg, cs, locked)
                        except Failed:
                            pass
                        else:
                            alternatives.append((getweight(cs), cs))

        # Check if downgrading is possible.
        for prv in pkg.provides:
            for upg in prv.upgradedby:
                for upgpkg in upg.packages:
                    if upgpkg not in locked:
                        cs = changeset.copy()
                        try:
                            self.install(upgpkg, cs, locked)
                        except Failed:
                            pass
                        else:
                            alternatives.append((getweight(cs), cs))

        alternatives.sort()
        changeset.setState(alternatives[0][1])

    def install(self, pkg, changeset=None, locked=None):
        if locked is None:
            locked = self._policy.getLockedSet().copy()
        else:
            locked = locked.copy()
        if pkg in locked:
            raise Failed, "can't install %s: it's locked" % pkg
        locked[pkg] = True
        if changeset is None:
            changeset = self._changeset
        changeset.setInstall(pkg)
        isinst = changeset.isInstalled
        getweight = self._policy.getWeight

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

        # Remove packages with the same name-version that can't
        # coexist with this one.
        namepkgs = self._cache.getPackages(pkg.name)
        for namepkg in namepkgs:
            if (namepkg is not pkg and isinst(namepkg) and
                not pkg.coexists(namepkg)):
                self.remove(namepkg, changeset, locked)

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
                preceddct = {}
                for prvpkg in prvpkgs:
                    lst = preceddct.get(prvpkg.precedence)
                    if lst:
                        lst.append(prvpkg)
                    else:
                        preceddct[prvpkg.precedence] = [prvpkg]
                precedlst = [(-x, preceddct[x]) for x in preceddct]
                precedlst.sort()
                for preced, prvpkgs in precedlst:
                    sortUpgrades(prvpkgs)
                    for prvpkg in prvpkgs:
                        try:
                            cs = changeset.copy()
                            self.install(prvpkg, cs, locked)
                        except Failed, e:
                            failures.append(str(e))
                        else:
                            alternatives.append((getweight(cs), cs))
                    if alternatives:
                        break
                if not alternatives:
                    raise Failed, "can't install %s: all packages providing " \
                                  "%s failed to install: %s" \
                                  % (pkg, req,  "; ".join(failures))
                alternatives.sort()
                changeset.setState(alternatives[0][1])
            else:
                self.install(prvpkgs[0], changeset, locked)

    def remove(self, pkg, changeset=None, locked=None):
        if pkg.essential:
            raise Failed, "can't remove %s: it's an essential package"
        if locked is None:
            locked = self._policy.getLockedSet().copy()
        else:
            locked = locked.copy()
        if pkg in locked:
            raise Failed, "can't remove %s: it's locked" % pkg
        locked[pkg] = True
        if changeset is None:
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
                lckd.update(dict.fromkeys(prvpkgs))
                
                # Try to install other providing packages.
                preceddct = {}
                for prvpkg in prvpkgs:
                    lst = preceddct.get(prvpkg.precedence)
                    if lst:
                        lst.append(prvpkg)
                    else:
                        preceddct[prvpkg.precedence] = [prvpkg]
                precedlst = [(-x, preceddct[x]) for x in preceddct]
                precedlst.sort()
                for preced, prvpkgs in precedlst:
                    sortUpgrades(prvpkgs)
                    for prvpkg in prvpkgs:
                        try:
                            cs = changeset.copy()
                            self.install(prvpkg, cs, locked)
                        except Failed, e:
                            failures.append(str(e))
                        else:
                            alternatives.append((getweight(cs), cs))
                    if alternatives:
                        break
                if prvpkgs:
                    for prvpkg in prvpkgs:
                        try:
                            cs = changeset.copy()
                            self.install(prvpkg, cs, locked)
                        except Failed, e:
                            failures.append(str(e))
                        else:
                            alternatives.append((getweight(cs), cs))

                # Then, remove every requiring package, or
                # upgrade/downgrade them to something which
                # does not require this dependency. lckd ensures
                # that the providing packages we just checked won't
                # be considered alternatives again.
                cs = changeset.copy()
                try:
                    for reqpkg in req.packages:
                        if not isinst(reqpkg):
                            continue
                        if reqpkg in locked:
                            raise Failed, "%s is locked" % reqpkg
                        self._remove(reqpkg, cs, lckd)
                except Failed, e:
                    failures.append(str(e))
                else:
                    alternatives.append((getweight(cs), cs))

                if not alternatives:
                    raise Failed, "can't remove %s: %s is being required " \
                                  "and all alternatives failed: %s" % \
                                  (pkg, prv, "; ".join(failures))

                alternatives.sort()
                changeset.setState(alternatives[0][1])

    def upgrade(self, pkgs, changeset=None, locked=None):
        if locked is None:
            locked = self._policy.getLockedSet().copy()
            locked.update(self._policy.getUpgradeLockedSet())
        else:
            locked = locked.copy()
        if changeset is None:
            changeset = self._changeset
        isinst = changeset.isInstalled

        if type(pkgs) is not list:
            pkgs = [pkgs]

        # Find packages upgrading given packages.
        upgpkgs = {}
        for pkg in pkgs:
            if isinst(pkg):
                for prv in pkg.provides:
                    for upg in prv.upgradedby:
                        for upgpkg in upg.packages:
                            if (upgpkg in locked or
                                upgpkg in upgpkgs or
                                isinst(upgpkg)):
                                continue
                            upgpkgs[upgpkg] = True

        self.evalBestState(upgpkgs.keys(), changeset, locked,
                           install=True, keep=True)

    def evalBestState(self, pkgs, changeset=None, locked=None,
                      install=False, remove=False, keep=False, upgrade=False):
        if locked is None:
            locked = self._policy.getLockedSet().copy()
        else:
            locked = locked.copy()
        if changeset is None:
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
                    self.install(pkg, cs, locked)
                except Failed, e:
                    failures.append(str(e))
                else:
                    alternatives.append((getweight(cs), cs))

            if remove:
                try:
                    cs = changeset.copy()
                    self.remove(pkg, cs, locked)
                except Failed, e:
                    failures.append(str(e))
                else:
                    alternatives.append((getweight(cs), cs))

            if upgrade:
                try:
                    cs = changeset.copy()
                    self.upgrade(pkg, cs, locked)
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

    def minimize(self, changeset=None, locked=None):
        if changeset is None:
            changeset = self._changeset
        if locked is None:
            locked = self._policy.getLockedSet().copy()
        else:
            locked = locked.copy()
        getweight = self._policy.getWeight
        set = changeset.getSet()
        bestweight = getweight(changeset)
        for pkg in set.keys():
            if pkg not in set or pkg in locked:
                continue
            if set[pkg] is INSTALL:
                if not pkg.installed:
                    cs = changeset.copy()
                    try:
                        self.remove(pkg, cs, locked)
                    except Failed:
                        pass
                    else:
                        weight = getweight(cs)
                        if weight < bestweight:
                            bestweight = weight
                            changeset.setState(cs)
            else:
                if pkg.installed:
                    cs = changeset.copy()
                    try:
                        self.install(pkg, cs, locked)
                    except Failed:
                        pass
                    else:
                        weight = getweight(cs)
                        if weight < bestweight:
                            bestweight = weight
                            changeset.setState(cs)

class ChangeSetSplitter:
    # An upgrade should never be split from the old package erasure!

    def __init__(self, changeset):
        self._changeset = changeset
        self._forcerequires = False
        self._locked = {}

    def getForceRequires(self):
        return self._userequires

    def setForceRequires(self, flag):
        self._forcerequires = flag

    def getLocked(self, pkg):
        return pkg in self._locked

    def setLocked(self, pkg, flag):
        if flag:
            self._locked[pkg] = True
        else:
            if pkg in self._locked:
                del self._locked[pkg]

    def setLockedSet(self, set):
        self._locked.clear()
        self._locked.update(set)

    def resetLocked(self):
        self._locked.clear()

    def include(self, changeset, pkg):
        set = changeset.getSet()
        selfset = self._changeset.getSet()
        # Try to include pkg in the changeset, if it won't
        # require changing the state of other locked packages.
        # If installing, add every requires/pre-requires for pkg
        # If removing, remove every requires/pre-requires for pkg
        pass

    def exclude(self, changeset, pkg):
        # Try to exclude package from the changeset, it it won't
        # have to change the state of other locked packages.
        pass

    def includeAll(self, changeset):
        # Do everything that doesn't change locked packages
        pass

    def excludeAll(self, changeset):
        # Keep everything that doesn't change locked packages
        pass

def sortUpgrades(pkgs):
    upgpkgs = {}
    for pkg in pkgs:
        dct = {}
        rupg = recursiveUpgrades(pkg, dct)
        del dct[pkg]
        upgpkgs[pkg] = dct
    pkgs.sort()
    pkgs.reverse()
    newpkgs = []
    for pkg in pkgs:
        pkgupgs = upgpkgs[pkg]
        for i in range(len(newpkgs)):
            if newpkgs[i] in pkgupgs:
                newpkgs.insert(i, pkg)
                break
        else:
            newpkgs.append(pkg)
    pkgs[:] = newpkgs

def recursiveUpgrades(pkg, set):
    set[pkg] = True
    for upg in pkg.upgrades:
        for prv in upg.providedby:
            for prvpkg in prv.packages:
                if prvpkg not in set:
                    recursiveUpgrades(prvpkg, set)

try:
    import psyco
except ImportError:
    pass
else:
    psyco.bind(Transaction)

# vim:ts=4:sw=4:et

from cpm.const import INSTALL, REMOVE
from cpm.cache import PreRequires
from cpm import *

class ChangeSet(dict):
    def __init__(self, state=None):
        if state:
            self.update(state)

    def getState(self):
        return self.copy()

    def setState(self, state):
        self.clear()
        self.update(state)
        return self

    def copy(self):
        return ChangeSet(self)

    def set(self, pkg, op):
        if op is INSTALL:
            if pkg.installed:
                if pkg in self:
                    del self[pkg]
            else:
                self[pkg] = INSTALL
        else:
            if not pkg.installed:
                if pkg in self:
                    del self[pkg]
            else:
                self[pkg] = REMOVE

    def installed(self, pkg):
        op = self.get(pkg)
        return op is INSTALL or pkg.installed and not op is REMOVE

    def difference(self, other):
        diff = ChangeSet()
        for pkg in self:
            sop = self[pkg]
            if sop is not other.get(pkg):
                diff[pkg] = sop
        return diff

    def intersect(self, other):
        isct = ChangeSet()
        for pkg in self:
            sop = self[pkg]
            if sop is other.get(pkg):
                isct[pkg] = sop
        return isct

    def __str__(self):
        l = []
        for pkg in self:
            l.append("%s %s\n" % (self[pkg] is INSTALL and "I" or "R", pkg))
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
        # Compute upgrading/upgraded packages
        upgrading = {}
        upgraded = {}
        for pkg in changeset:
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if prvpkg.installed:
                            upgrading[pkg] = True
                            if changeset.get(prvpkg) is REMOVE:
                                upgraded[pkg] = True
        for pkg in changeset:
            op = changeset[pkg]
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
        for pkg in changeset:
            if changeset[pkg] is REMOVE:
                weight += 1
            else:
                weight += 5
        return weight

class PolicyUpgrade(Policy):
    """Give precedence to the choice with more upgrades and smaller impact."""

    def getWeight(self, changeset):
        weight = 0
        # Compute upgrading/upgraded packages
        upgrading = {}
        upgraded = {}
        for pkg in changeset:
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if prvpkg.installed:
                            # Check if another package has already upgraded
                            # this one. Two different packages upgrading the
                            # same package is not valuable.
                            if prvpkg not in upgraded:
                                upgrading[pkg] = True
                                if changeset.get(prvpkg) is REMOVE:
                                    upgraded[prvpkg] = True
        for pkg in changeset:
            op = changeset[pkg]
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

    def installed(self, pkg):
        return self._changeset.installed(pkg)

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
        changeset.set(pkg, INSTALL)
        isinst = changeset.installed
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
        changeset.set(pkg, REMOVE)
        isinst = changeset.installed
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
        isinst = changeset.installed

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

        if upgpkgs:
            self.evalBestState(upgpkgs.keys(), changeset, locked,
                               install=True, keep=True)

    def fix(self, pkgs):
        changeset = self._changeset
        isinst = changeset.installed

        fixpkgs = {}
        for pkg in pkgs:
            if isinst(pkg):
                # Is it broken?
                try:
                    for req in pkg.requires:
                        for prv in req.providedby:
                            for prvpkg in prv.packages:
                                if isinst(prvpkg):
                                    break
                            else:
                                continue
                            break
                        else:
                            logger.debug("unsatisfied dependency: "
                                         "%s requires %s" % (pkg, req))
                            raise Failed
                    for cnf in pkg.conflicts:
                        for prv in cnf.providedby:
                            for prvpkg in prv.packages:
                                if isinst(prvpkg):
                                    logger.debug("unsatisfied dependency: "
                                                 "%s conflicts with %s"
                                                 % (pkg, prvpkg))
                                    raise Failed
                    for prv in pkg.provides:
                        for cnf in prv.conflictedby:
                            for cnfpkg in cnf.packages:
                                if isinst(cnfpkg):
                                    logger.debug("unsatisfied dependency: "
                                                 "%s conflicts with %s"
                                                 % (cnfpkg, pkg))
                                    raise Failed
                except Failed:
                    fixpkgs[pkg] = True

        self.evalBestState(fixpkgs.keys(), install=True,
                           remove=True, removeupgrade=True)

    def evalBestState(self, pkgs, changeset=None, locked=None,
                      install=False, remove=False, keep=False,
                      upgrade=False, removeupgrade=False):
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
                    if not cs.difference(changeset):
                        cs = None
                except Failed, e:
                    failures.append(str(e))
                else:
                    if cs:
                        alternatives.append((getweight(cs), cs))

            if removeupgrade:
                try:
                    cs = changeset.copy()
                    self.remove(pkg, cs, locked)
                    removecs = cs.copy()
                    self.upgrade(pkg, cs, locked)
                    if not cs.difference(removecs):
                        cs = None
                except Failed, e:
                    failures.append(str(e))
                else:
                    if cs:
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
        # Lock everything which is not in the changeset.
        for pkg in self._cache.getPackages():
            if pkg not in changeset:
                locked[pkg] = True
        bestweight = getweight(changeset)
        for pkg in changeset.keys():
            if pkg not in changeset or pkg in locked:
                continue
            if changeset[pkg] is INSTALL:
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
    # This class operates on *sane* changesets.

    def __init__(self, changeset, forcerequires=True):
        self._changeset = changeset
        self._forcerequires = forcerequires
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

    def include(self, changeset, pkg, locked=None):
        # Try to include pkg in the subset, if it won't
        # require changing the state of other locked packages.
        set = self._changeset
        subset = changeset

        if locked is None:
            locked = self._locked
        else:
            locked = locked.copy()

        if pkg in locked:
            raise Error, "package '%s' is locked" % pkg

        locked[pkg] = True

        if pkg in subset:
            return
        if pkg not in set:
            raise Error, "package '%s' is not in changeset" % pkg

        try:
            if set[pkg] is INSTALL:
                subset[pkg] = INSTALL

                # Check all dependencies needed by this package.
                for req in pkg.requires:

                    # We try to include all required dependencies selected
                    # for installation, even if not mandatory.
                    found = False
                    for prv in req.providedby:
                        for prvpkg in prv.packages:
                            if subset.get(prvpkg) is INSTALL:
                                found = True
                            elif (set.get(prvpkg) is INSTALL and not
                                prvpkg in locked):
                                try:
                                    self.include(changeset, prvpkg, locked)
                                    found = True
                                except Error:
                                    pass
                                else:
                                    break
                    if found:
                        continue

                    # We couldn't solve the problem with any solution in
                    # the changeset. Let's hope some installed package
                    # may do the job.
                    found = False
                    for prv in req.providedby:
                        for prvpkg in prv.packages:
                            if (prvpkg.installed and
                                subset.get(prvpkg) is not REMOVE):
                                found = True
                                break
                        else:
                            continue
                        break
                    if found:
                        continue

                    # There are no solutions for the problem.
                    # Should we really care about it?
                    if (self._forcerequires or
                        isinstance(req, PreRequires)):
                        raise Error, "no providers for '%s'" % req

                # About conflicts there's nothing we can do. Any
                # conflicting/conflicted package must leave.
                cnfpkgs = [prvpkg for cnf in pkg.conflicts
                                  for prv in cnf.providedby
                                  for prvpkg in prv.packages]
                cnfpkgs.extend([cnfpkg for prv in pkg.provides
                                       for cnf in prv.conflictedby
                                       for cnfpkg in cnf.packages])
                for cnfpkg in cnfpkgs:
                    if cnfpkg.installed and subset.get(cnfpkg) is not REMOVE:
                        if set.get(cnfpkg) is not REMOVE:
                            raise Error, "broken changeset: '%s' is not " \
                                         "selected for being removed" % \
                                         cnfpkg
                        elif cnfpkg in locked:
                            raise Error, "'%s' must be removed but is " \
                                         "locked" % cnfpkg
                        else:
                            self.include(changeset, cnfpkg, locked)

                # Include upgraded packages being removed as well. We
                # can't split an upgrade from the package erasure.
                for upg in pkg.upgrades:
                    for prv in upg.providedby:
                        for prvpkg in prv.packages:
                            if (set.get(prvpkg) is REMOVE
                                and prvpkg not in subset):
                                if prvpkg in locked:
                                    raise Error, "package '%s' is locked" % \
                                                 prvpkg
                                self.include(changeset, prvpkg, locked)

            else: # if set[pkg] is REMOVE
                subset[pkg] = REMOVE

                # Include requiring packages being removed, or exclude
                # requiring packages being installed.
                for prv in pkg.provides:
                    for req in prv.requiredby:
                        for reqpkg in req.packages:

                            if (subset.get(reqpkg) is REMOVE or
                                (subset.get(reqpkg) is not INSTALL and
                                 not pkg.installed)):
                                # No problems.
                                continue

                            # Someone else may be providing it. Check
                            # if we may try to install it, or if it will
                            # stay in the system.
                            found = False
                            for prv in req.providedby:
                                for prvpkg in prv.packages:
                                    if (subset.get(prvpkg) is INSTALL or
                                        (prvpkg.installed and not
                                         subset.get(prvpkg) is REMOVE)):
                                        # Already there. Great.
                                        found = True
                                        break
                                else:
                                    continue
                                break
                            if found:
                                # This fixes every requiring package
                                # problem, so we may break here.
                                break

                            # Check if there's any providing package
                            # we may try to install.
                            for prv in req.providedby:
                                for prvpkg in prv.packages:
                                    if (set.get(prvpkg) is INSTALL
                                        and prvpkg not in locked):
                                        try:
                                            self.include(changeset, prvpkg,
                                                         locked)
                                        except Error:
                                            pass
                                        else:
                                            found = True
                                            break
                            if found:
                                # This fixes every requiring package
                                # problem, so we may break here.
                                break

                            # Finally, try to include the requiring
                            # package, if it's being removed, or exclude
                            # it, if it's being installed. This solves
                            # this package's problem only, so we must
                            # continue checking the list of requiring
                            # packages.
                            if reqpkg not in locked:
                                try:
                                    if set.get(reqpkg) is REMOVE:
                                        self.include(changeset, reqpkg,
                                                     locked)
                                    elif set.get(reqpkg) is INSTALL:
                                        self.exclude(changeset, reqpkg,
                                                     locked)
                                except Error:
                                    pass
                                else:
                                    continue

                            # We can't do anything about it.
                            # Is it serious?
                            if (self._forcerequires or
                                isinstance(req, PreRequires)):
                                raise Error, "no other providers for " \
                                             "'%s'" % req


                # Every upgrading package must be included.
                for prv in pkg.provides:
                    for upg in prv.upgradedby:
                        for upgpkg in upg.packages:
                            if (subset.get(upgpkg) is not INSTALL and
                                set.get(upgpkg) is INSTALL):
                                if upgpkg in locked:
                                    raise Error, "package '%s' is locked" % \
                                                 upgpkg
                                self.include(changeset, upgpkg, locked)

        except Error:
            del subset[pkg]
            raise

    def exclude(self, changeset, pkg, locked=None):
        # Try to exclude package from the changeset, it it won't
        # have to change the state of other locked packages.
        set = self._changeset
        subset = changeset

        if locked is None:
            locked = self._locked
        else:
            locked = locked.copy()

        if pkg in locked:
            raise Error, "package '%s' is locked" % pkg

        locked[pkg] = True

        if pkg not in set:
            raise Error, "package '%s' is not in changeset" % pkg
        if pkg not in subset:
            return

        op = set[pkg]
        try:
            del subset[pkg]
            if op is INSTALL:

                # Exclude every package that depends exclusively on
                # this package, or include an available alternative.
                for prv in pkg.provides:
                    for req in prv.requiredby:
                        for reqpkg in req.packages:

                            if (subset.get(reqpkg) is REMOVE or
                                (subset.get(reqpkg) is not INSTALL and
                                 not pkg.installed)):
                                # No problems.
                                continue

                            # Check if some package that will stay
                            # in the system, or some package selected
                            # for installation, is still providing
                            # the dependency.
                            found = False
                            for prv in req.providedby:
                                for prvpkg in prv.packages:
                                    if (subset.get(prvpkg) is INSTALL or
                                        (prvpkg.installed and not
                                         subset.get(prvpkg) is REMOVE)):
                                        found = True
                                        break
                                else:
                                    continue
                                break
                            if found:
                                # This solves the problem of all
                                # requiring packages, so we may break
                                # here.
                                break

                            # Try to include some providing package
                            # that is selected for installation.
                            found = False
                            for prv in req.providedby:
                                for prvpkg in prv.packages:
                                    if (set.get(prvpkg) is INSTALL and
                                        prvpkg not in locked):
                                        try:
                                            self.include(changeset, prvpkg,
                                                         locked)
                                        except Error:
                                            pass
                                        else:
                                            found = True
                                            break
                                else:
                                    continue
                                break
                            if found:
                                # This solves the problem of all
                                # requiring packages, so we may break
                                # here.
                                break

                            # Finally, try to exclude the requiring
                            # package if it is being installed, or
                            # include it if it's being removed. This
                            # solves this package's problem only,
                            # so we must continue checking the list
                            # of requiring packages.
                            if reqpkg not in locked:
                                try:
                                    if set.get(reqpkg) is INSTALL:
                                        self.exclude(changeset, reqpkg,
                                                     locked)
                                    elif set.get(reqpkg) is REMOVE:
                                        self.include(changeset, reqpkg,
                                                     locked)
                                except Error:
                                    # Should we care about this?
                                    if (self._forcerequires or
                                        isinstance(req, PreRequires)):
                                        raise

                # Exclude upgraded packages being removed as well.
                for upg in pkg.upgrades:
                    for prv in upg.providedby:
                        for prvpkg in prv.packages:
                            if subset.get(prvpkg) is REMOVE:
                                if prvpkg in locked:
                                    raise Error, "package '%s' is locked" % \
                                                 prvpkg
                                self.exclude(changeset, prvpkg, locked)

            else: # if op is REMOVE

                # Package will stay in the system. Exclude conflicting
                # packages selected for installation.
                cnfpkgs = [prvpkg for cnf in pkg.conflicts
                                  for prv in cnf.providedby
                                  for prvpkg in prv.packages]
                cnfpkgs.extend([cnfpkg for prv in pkg.provides
                                       for cnf in prv.conflictedby
                                       for cnfpkg in cnf.packages])
                for cnfpkg in cnfpkgs:
                    if subset.get(cnfpkg) is INSTALL:
                        if cnfpkg in locked:
                            raise Error, "package '%s' is locked" % cnfpkg
                        self.exclude(changeset, cnfpkg, locked)

        except Error:
            subset[pkg] = op
            raise

    def includeAll(self, changeset):
        # Include everything that doesn't change locked packages
        set = self._changeset.get()
        for pkg in set.keys():
            try:
                self.include(changeset, pkg)
            except Error:
                pass

    def excludeAll(self, changeset):
        # Exclude everything that doesn't change locked packages
        set = self._changeset.get()
        for pkg in set.keys():
            try:
                self.exclude(changeset, pkg)
            except Error:
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

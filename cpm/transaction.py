from cpm.const import INSTALL, REMOVE, UPGRADE, FIX
from cpm.cache import PreRequires
from cpm import *

class ChangeSet(dict):

    def __init__(self, cache, state=None):
        self._cache = cache
        if state:
            self.update(state)

    def getCache(self):
        return self._cache

    def getState(self):
        return self.copy()

    def setState(self, state):
        self.clear()
        self.update(state)

    def getPersistentState(self):
        state = {}
        for pkg in self:
            state[(pkg.__class__, pkg.name, pkg.version)] = self[pkg]
        return state

    def setPersistentState(self, state):
        self.clear()
        for pkg in self._cache.getPackages():
            op = state.get((pkg.__class__, pkg.name, pkg.version))
            if op is not None:
                self[pkg] = op

    def copy(self):
        return ChangeSet(self._cache, self)

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
        diff = ChangeSet(self._cache)
        for pkg in self:
            sop = self[pkg]
            if sop is not other.get(pkg):
                diff[pkg] = sop
        return diff

    def intersect(self, other):
        isct = ChangeSet(self._cache)
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

    def __init__(self, trans):
        self._trans = trans
        self._locked = {}
        self._sysconflocked = []
        self._priorities = {}

    def runStarting(self):
        self._priorities.clear()
        cache = self._trans.getCache()
        for pkg in sysconf.filterByFlag("lock", cache.getPackages()):
            if pkg not in self._locked:
                self._sysconflocked.append(pkg)
                self._locked[pkg] = True

    def runFinished(self):
        self._priorities.clear()
        for pkg in self._sysconflocked:
            del self._locked[pkg]
        del self._sysconflocked[:]

    def getLocked(self, pkg):
        return pkg in self._locked

    def setLocked(self, pkg, flag):
        if flag:
            self._locked[pkg] = True
        else:
            if pkg in self._locked:
                del self._locked[pkg]

    def getLockedSet(self):
        return self._locked

    def getWeight(self, changeset):
        return 0

    def getPriority(self, pkg):
        priority = self._priorities.get(pkg)
        if priority is None:
            self._priorities[pkg] = priority = pkg.getPriority()
        return priority

    def getPriorityWeights(self, pkgs):
        set = {}
        lower = None
        for pkg in pkgs:
            priority = self.getPriority(pkg)
            if lower is None or priority < lower:
                lower = priority
            set[pkg] = priority
        for pkg in set:
            set[pkg] = -(set[pkg] - lower)
        return set

class PolicyInstall(Policy):
    """Give precedence for keeping functionality in the system."""

    def runStarting(self):
        Policy.runStarting(self)
        self._upgrading = upgrading = {}
        self._upgraded = upgraded = {}
        for pkg in self._trans.getCache().getPackages():
            # Precompute upgrade relations.
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if (prvpkg.installed and
                            self.getPriority(pkg) >= self.getPriority(prvpkg)):
                            upgrading[pkg] = True
                            if prvpkg in upgraded:
                                upgraded[prvpkg].append(pkg)
                            else:
                                upgraded[prvpkg] = [pkg]
            # Downgrades are upgrades if they have a higher priority.
            for prv in pkg.provides:
                for upg in prv.upgradedby:
                    for upgpkg in upg.packages:
                        if (upgpkg.installed and
                            self.getPriority(pkg) > self.getPriority(upgpkg)):
                            upgrading[pkg] = True
                            if upgpkg in upgraded:
                                upgraded[prvpkg].append(pkg)
                            else:
                                upgraded[prvpkg] = [pkg]

    def runFinished(self):
        Policy.runFinished(self)
        del self._upgrading
        del self._upgraded

    def getWeight(self, changeset):
        weight = 0
        upgrading = self._upgrading
        upgraded = self._upgraded
        for pkg in changeset:
            if changeset[pkg] is REMOVE:
                # Upgrading a package that will be removed
                # is better than upgrading a package that will
                # stay in the system.
                lst = upgraded.get(pkg, ())
                for lstpkg in lst:
                    if changeset.get(lstpkg) is INSTALL:
                        weight -= 1
                        break
                else:
                    weight += 20
            else:
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

    def runStarting(self):
        Policy.runStarting(self)
        self._upgrading = upgrading = {}
        self._upgraded = upgraded = {}
        self._bonus = bonus = {}
        queue = self._trans.getQueue()
        for pkg in self._trans.getCache().getPackages():
            # Precompute upgrade relations.
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if (prvpkg.installed and
                            self.getPriority(pkg) >= self.getPriority(prvpkg)):
                            upgrading[pkg] = True
                            if prvpkg in upgraded:
                                upgraded[prvpkg].append(pkg)
                            else:
                                upgraded[prvpkg] = [pkg]
            # Downgrades are upgrades if they have a higher priority.
            for prv in pkg.provides:
                for upg in prv.upgradedby:
                    for upgpkg in upg.packages:
                        if (upgpkg.installed and
                            self.getPriority(pkg) > self.getPriority(upgpkg)):
                            upgrading[pkg] = True
                            if upgpkg in upgraded:
                                upgraded[prvpkg].append(pkg)
                            else:
                                upgraded[prvpkg] = [pkg]
            # Precompute bonus weight for installing packages
            # required for other upgrades.
            weight = 0
            for prv in pkg.provides:
                for req in prv.requiredby:
                    for reqpkg in req.packages:
                        if queue.get(reqpkg) is UPGRADE:
                            weight -= 3
            if weight:
                bonus[pkg] = weight

    def runFinished(self):
        Policy.runFinished(self)
        del self._upgrading
        del self._upgraded
        del self._bonus

    def getWeight(self, changeset):
        weight = 0
        upgrading = self._upgrading
        upgraded = self._upgraded
        bonus = self._bonus
        for pkg in changeset:
            if changeset[pkg] is REMOVE:
                # Upgrading a package that will be removed
                # is better than upgrading a package that will
                # stay in the system.
                lst = upgraded.get(pkg, ())
                for lstpkg in lst:
                    if changeset.get(lstpkg) is INSTALL:
                        weight -= 1
                        break
                else:
                    weight += 3
            else:
                if pkg in upgrading:
                    weight -= 4
                else:
                    weight += 1
                weight += bonus.get(pkg, 0)
        return weight

class Failed(Error): pass

PENDING_REMOVE   = 1
PENDING_INSTALL  = 2
PENDING_UPDOWN   = 3

class Transaction(object):
    def __init__(self, cache, policy=None, changeset=None, queue=None):
        self._cache = cache
        self._policy = policy and policy(self) or Policy(self)
        self._changeset = changeset or ChangeSet(cache)
        self._queue = queue or {}

    def clear(self):
        self._changeset.clear()
        self._queue.clear()

    def getCache(self):
        return self._cache

    def getQueue(self):
        return self._queue

    def getPolicy(self):
        return self._policy

    def setPolicy(self, policy):
        self._policy = policy(self)

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

    def __nonzero__(self):
        return bool(self._changeset)

    def __str__(self):
        return str(self._changeset)

    def _install(self, pkg, changeset, locked, pending, depth=0):
        #print "[%03d] _install(%s)" % (depth, pkg)
        depth += 1

        locked[pkg] = True
        changeset.set(pkg, INSTALL)
        isinst = changeset.installed

        # Remove packages conflicted by this one.
        for cnf in pkg.conflicts:
            for prv in cnf.providedby:
                for prvpkg in prv.packages:
                    if not isinst(prvpkg):
                        locked[prvpkg] = True
                        continue
                    if prvpkg in locked:
                        raise Failed, "Can't install %s: conflicted package " \
                                      "%s is locked" % (pkg, prvpkg)
                    self._remove(prvpkg, changeset, locked, pending, depth)
                    pending.append((PENDING_UPDOWN, prvpkg))

        # Remove packages conflicting with this one.
        for prv in pkg.provides:
            for cnf in prv.conflictedby:
                for cnfpkg in cnf.packages:
                    if not isinst(cnfpkg):
                        locked[cnfpkg] = True
                        continue
                    if cnfpkg in locked:
                        raise Failed, "Can't install %s: it's conflicted by " \
                                      "the locked package %s" % (pkg, cnfpkg)
                    self._remove(cnfpkg, changeset, locked, pending, depth)
                    pending.append((PENDING_UPDOWN, cnfpkg))

        # Remove packages with the same name that can't
        # coexist with this one.
        namepkgs = self._cache.getPackages(pkg.name)
        for namepkg in namepkgs:
            if namepkg is not pkg and not pkg.coexists(namepkg):
                if not isinst(namepkg):
                    locked[namepkg] = True
                    continue
                if namepkg in locked:
                    raise Failed, "Can't install %s: it can't coexist " \
                                  "with %s" % (pkg, namepkg)
                self._remove(namepkg, changeset, locked, pending, depth)

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

            if not prvpkgs:
                # No packages provide it at all. Give up.
                raise Failed, "Can't install %s: no package provides %s" % \
                              (pkg, req)

            if len(prvpkgs) == 1:
                # Don't check locked here. prvpkgs was
                # already filtered above.
                self._install(prvpkgs.popitem()[0], changeset, locked,
                              pending, depth)
            else:
                # More than one package provide it. This package
                # must be post-processed.
                pending.append((PENDING_INSTALL, pkg, req, prvpkgs.keys()))

    def _remove(self, pkg, changeset, locked, pending, depth=0):
        #print "[%03d] _remove(%s)" % (depth, pkg)
        depth += 1

        if pkg.essential:
            raise Failed, "Can't remove %s: it's an essential package"

        locked[pkg] = True
        changeset.set(pkg, REMOVE)
        isinst = changeset.installed

        # Check packages requiring this one.
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

                if prvpkgs:
                    # There are other options, besides removing.
                    pending.append((PENDING_REMOVE, pkg, prv, req.packages,
                                    prvpkgs.keys()))
                else:
                    # Remove every requiring package, or
                    # upgrade/downgrade them to something which
                    # does not require this dependency.
                    for reqpkg in req.packages:
                        if not isinst(reqpkg):
                            continue
                        if reqpkg in locked:
                            raise Failed, "%s is locked" % reqpkg
                        self._remove(reqpkg, changeset, locked, pending, depth)
                        pending.append((PENDING_UPDOWN, reqpkg))

    def _updown(self, pkg, changeset, locked, depth=0):
        #print "[%03d] _updown(%s)" % (depth, pkg)
        depth += 1

        isinst = changeset.installed
        getpriority = self._policy.getPriority

        pkgpriority = getpriority(pkg)

        # Check if any upgrading version of this package is installed.
        # If so, we won't try to install any other version.
        upgpkgs = {}
        for prv in pkg.provides:
            for upg in prv.upgradedby:
                for upgpkg in upg.packages:
                    if isinst(upgpkg):
                        return
                    if getpriority(upgpkg) < pkgpriority:
                        continue
                    if upgpkg not in locked and upgpkg not in upgpkgs:
                        upgpkgs[upgpkg] = True
        # Also check if any downgrading version with a higher
        # priority is installed.
        for upg in pkg.upgrades:
            for prv in upg.providedby:
                for prvpkg in prv.packages:
                    if getpriority(prvpkg) <= pkgpriority:
                        continue
                    if isinst(prvpkg):
                        return
                    if prvpkg not in locked and prvpkg not in upgpkgs:
                        upgpkgs[prvpkg] = True

        # No, let's try to upgrade it.
        getweight = self._policy.getWeight
        alternatives = [(getweight(changeset), changeset)]

        # Check if upgrading is possible.
        for upgpkg in upgpkgs:
            try:
                cs = changeset.copy()
                lk = locked.copy()
                _pending = []
                self._install(upgpkg, cs, lk, _pending, depth)
                if _pending:
                    self._pending(cs, lk, _pending, depth)
            except Failed:
                pass
            else:
                alternatives.append((getweight(cs), cs))

        # Is any downgrading version of this package installed?
        try:
            dwnpkgs = {}
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if getpriority(prvpkg) > pkgpriority:
                            continue
                        if isinst(prvpkg):
                            raise StopIteration
                        if prvpkg not in locked:
                            dwnpkgs[prvpkg] = True
            # Also check if any upgrading version with a lower
            # priority is installed.
            for prv in pkg.provides:
                for upg in prv.upgradedby:
                    for upgpkg in upg.packages:
                        if getpriority(upgpkg) >= pkgpriority:
                            continue
                        if isinst(upgpkg):
                            raise StopIteration
                        if upgpkg not in locked:
                            dwnpkgs[upgpkg] = True
        except StopIteration:
            pass
        else:
            # Check if downgrading is possible.
            for dwnpkg in dwnpkgs:
                try:
                    cs = changeset.copy()
                    lk = locked.copy()
                    _pending = []
                    self._install(dwnpkg, cs, lk, _pending, depth)
                    if _pending:
                        self._pending(cs, lk, _pending, depth)
                except Failed:
                    pass
                else:
                    alternatives.append((getweight(cs), cs))

        if len(alternatives) > 1:
            alternatives.sort()
            changeset.setState(alternatives[0][1])

    def _pending(self, changeset, locked, pending, depth=0):
        #print "[%03d] _pending(%s)" % depth
        depth += 1

        isinst = changeset.installed
        getweight = self._policy.getWeight

        updown = []
        while pending:
            item = pending.pop(0)
            kind = item[0]
            if kind == PENDING_UPDOWN:
                updown.append(item[1])
            elif kind == PENDING_INSTALL:
                kind, pkg, req, prvpkgs = item

                # Check if any prvpkg was already selected for installation
                # due to some other change.
                found = False
                for i in range(len(prvpkgs)-1,-1,-1):
                    prvpkg = prvpkgs[i]
                    if isinst(prvpkg):
                        found = True
                        break
                    if prvpkg in locked:
                        del prvpkgs[i]
                if found:
                    continue

                if not prvpkgs:
                    # No packages provide it at all. Give up.
                    raise Failed, "Can't install %s: no package provides %s" % \
                                  (pkg, req)

                if len(prvpkgs) > 1:
                    # More than one package provide it. We use _pending here,
                    # since any option must consider the whole change for
                    # weighting.
                    alternatives = []
                    failures = []
                    sortUpgrades(prvpkgs)
                    pw = self._policy.getPriorityWeights(prvpkgs)
                    for prvpkg in prvpkgs:
                        try:
                            _pending = []
                            cs = changeset.copy()
                            lk = locked.copy()
                            self._install(prvpkg, cs, lk, _pending, depth)
                            if _pending:
                                self._pending(cs, lk, _pending, depth)
                        except Failed, e:
                            failures.append(str(e))
                        else:
                            alternatives.append((getweight(cs)+pw[prvpkg],
                                                cs, lk))
                    if not alternatives:
                        raise Failed, "Can't install %s: all packages providing " \
                                      "%s failed to install:\n%s" \
                                      % (pkg, req,  "\n".join(failures))
                    alternatives.sort()
                    changeset.setState(alternatives[0][1])
                    if len(alternatives) == 1:
                        locked.update(alternatives[0][2])
                else:
                    # This turned out to be the only way.
                    self._install(prvpkgs[0], changeset, locked,
                                  pending, depth)

            elif kind == PENDING_REMOVE:
                kind, pkg, prv, reqpkgs, prvpkgs = item

                # Check if someone installed is still requiring it.
                reqpkgs = [x for x in reqpkgs if isinst(x)]
                if not reqpkgs:
                    continue

                # Check if someone installed is providing it.
                found = False
                for prvpkg in prvpkgs:
                    if isinst(prvpkg):
                        found = True
                        break
                if found:
                    # Someone is still providing it. Good.
                    continue

                prvpkgs = [x for x in prvpkgs if x not in locked]

                # No one is providing it anymore. We'll have to do
                # something about it.

                # Try to install other providing packages.
                if prvpkgs:

                    alternatives = []
                    failures = []

                    pw = self._policy.getPriorityWeights(prvpkgs)
                    for prvpkg in prvpkgs:
                        try:
                            _pending = []
                            cs = changeset.copy()
                            lk = locked.copy()
                            self._install(prvpkg, cs, lk, _pending, depth)
                            if _pending:
                                self._pending(cs, lk, _pending, depth)
                        except Failed, e:
                            failures.append(str(e))
                        else:
                            alternatives.append((getweight(cs)+pw[prvpkg],
                                                cs, lk))

                if not prvpkgs or not alternatives:

                    # There's no alternatives. We must remove
                    # every requiring package.

                    for reqpkg in reqpkgs:
                        if reqpkg in locked and isinst(reqpkg):
                            raise Failed, "Can't remove %s: requiring " \
                                          "package %s is locked" % \
                                          (pkg, reqpkg)
                    for reqpkg in reqpkgs:
                        # We check again, since other actions may have
                        # changed their state.
                        if not isinst(reqpkg):
                            continue
                        if reqpkg in locked:
                            raise Failed, "Can't remove %s: requiring " \
                                          "package %s is locked" % \
                                          (pkg, reqpkg)
                        self._remove(reqpkg, changeset, locked,
                                     pending, depth)
                    continue

                # Then, remove every requiring package, or
                # upgrade/downgrade them to something which
                # does not require this dependency.
                cs = changeset.copy()
                lk = locked.copy()
                try:
                    for reqpkg in reqpkgs:
                        if reqpkg in locked and isinst(reqpkg):
                            raise Failed, "%s is locked" % reqpkg
                    for reqpkg in reqpkgs:
                        if not cs.installed(reqpkg):
                            continue
                        if reqpkg in lk:
                            raise Failed, "%s is locked" % reqpkg
                        _pending = []
                        self._remove(reqpkg, cs, lk, _pending, depth)
                        if _pending:
                            self._pending(changeset, lk, _pending, depth)
                except Failed, e:
                    failures.append(str(e))
                else:
                    alternatives.append((getweight(cs), cs, lk))

                if not alternatives:
                    raise Failed, "Can't install %s: all packages providing " \
                                  "%s failed to install:\n%s" \
                                  % (pkg, prv,  "\n".join(failures))

                alternatives.sort()
                changeset.setState(alternatives[0][1])
                if len(alternatives) == 1:
                    locked.update(alternatives[0][2])

        for pkg in updown:
            self._updown(pkg, changeset, locked, depth)

        del pending[:]

    def _upgrade(self, pkgs, changeset, locked, pending, depth=0):
        #print "[%03d] _upgrade()" % depth
        depth += 1

        isinst = changeset.installed
        getweight = self._policy.getWeight
        queue = self._queue

        sortUpgrades(pkgs)

        weight = getweight(changeset)
        for pkg in pkgs:
            if pkg in locked or isinst(pkg):
                continue

            try:
                cs = changeset.copy()
                lk = locked.copy()
                _pending = []
                self._install(pkg, cs, lk, _pending, depth)
                if _pending:
                    self._pending(cs, lk, _pending, depth)
            except Failed:
                pass
            else:
                csweight = getweight(cs)
                if csweight < weight:
                    weight = csweight
                    changeset.setState(cs)

    def _fix(self, pkgs, changeset, locked, pending, depth=0):
        #print "[%03d] _fix()" % depth
        depth += 1

        getweight = self._policy.getWeight
        isinst = changeset.installed

        for pkg in pkgs:

            if not isinst(pkg):
                continue

            # Is it broken at all?
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
                        iface.debug("Unsatisfied dependency: "
                                    "%s requires %s" % (pkg, req))
                        raise StopIteration
                for cnf in pkg.conflicts:
                    for prv in cnf.providedby:
                        for prvpkg in prv.packages:
                            if isinst(prvpkg):
                                iface.debug("Unsatisfied dependency: "
                                            "%s conflicts with %s"
                                            % (pkg, prvpkg))
                                raise StopIteration
                for prv in pkg.provides:
                    for cnf in prv.conflictedby:
                        for cnfpkg in cnf.packages:
                            if isinst(cnfpkg):
                                iface.debug("Unsatisfied dependency: "
                                            "%s conflicts with %s"
                                            % (cnfpkg, pkg))
                                raise StopIteration
            except StopIteration:
                pass
            else:
                continue

            # We have a broken package. Fix it.

            alternatives = []
            failures = []

            # Try to fix by installing it.
            try:
                cs = changeset.copy()
                lk = locked.copy()
                _pending = []
                self._install(pkg, cs, lk, _pending, depth)
                if _pending:
                    self._pending(cs, lk, _pending, depth)
            except Failed, e:
                failures.append(str(e))
            else:
                alternatives.append((getweight(cs), cs))

            # Try to fix by removing it.
            try:
                cs = changeset.copy()
                lk = locked.copy()
                _pending = []
                self._remove(pkg, cs, lk, _pending, depth)
                if _pending:
                    self._pending(cs, lk, _pending, depth)
                self._updown(pkg, cs, lk, depth)
            except Failed, e:
                failures.append(str(e))
            else:
                alternatives.append((getweight(cs), cs))

            if not alternatives:
                raise Failed, "Can't fix %s:\n%s" % (pkg, "\n".join(failures))

            alternatives.sort()
            changeset.setState(alternatives[0][1])

    def enqueue(self, pkg, op):
        if op is UPGRADE:
            isinst = self._changeset.installed
            _upgpkgs = {}
            try:
                pkgpriority = pkg.getPriority()
                for prv in pkg.provides:
                    for upg in prv.upgradedby:
                        for upgpkg in upg.packages:
                            if upgpkg.getPriority() < pkgpriority:
                                continue
                            if isinst(upgpkg):
                                raise StopIteration
                            _upgpkgs[upgpkg] = True
                for upg in pkg.upgrades:
                    for prv in upg.providedby:
                        for prvpkg in prv.packages:
                            if prvpkg.getPriority() <= pkgpriority:
                                continue
                            if isinst(prvpkg):
                                raise StopIteration
                            _upgpkgs[prvpkg] = True
            except StopIteration:
                pass
            else:
                for upgpkg in _upgpkgs:
                    self._queue[upgpkg] = op
        else:
            self._queue[pkg] = op

    def run(self):

        self._policy.runStarting()

        try:
            changeset = self._changeset.copy()
            isinst = changeset.installed
            locked = self._policy.getLockedSet().copy()
            pending = []

            for pkg in self._queue:
                op = self._queue[pkg]
                if op is INSTALL:
                    if not isinst(pkg) and pkg in locked:
                        raise Failed, "Can't install %s: it's locked" % pkg
                    changeset.set(pkg, op)
                elif op is REMOVE:
                    if isinst(pkg) and pkg in locked:
                        raise Failed, "Can't remove %s: it's locked" % pkg
                    changeset.set(pkg, op)

            upgpkgs = []
            fixpkgs = []
            for pkg in self._queue:
                op = self._queue[pkg]
                if op is INSTALL:
                    self._install(pkg, changeset, locked, pending)
                elif op is REMOVE:
                    self._remove(pkg, changeset, locked, pending)
                elif op is UPGRADE:
                    upgpkgs.append(pkg)
                elif op is FIX:
                    fixpkgs.append(pkg)

            if pending:
                self._pending(changeset, locked, pending)

            if upgpkgs:
                self._upgrade(upgpkgs, changeset, locked, pending)

            if fixpkgs:
                self._fix(fixpkgs, changeset, locked, pending)

            self._changeset.setState(changeset)

        finally:
            self._queue.clear()
            self._policy.runFinished()


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
            raise Error, "Package '%s' is locked" % pkg

        locked[pkg] = True

        if pkg in subset:
            return
        if pkg not in set:
            raise Error, "Package '%s' is not in changeset" % pkg

        try:
            op = set[pkg]
            if op is INSTALL:
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
                        raise Error, "No providers for '%s'" % req

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
                            raise Error, "Broken changeset: '%s' is not " \
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
                                    raise Error, "Package '%s' is locked" % \
                                                 prvpkg
                                self.include(changeset, prvpkg, locked)

            elif op is REMOVE:
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
                                raise Error, "No other provider for " \
                                             "'%s'" % req


                # Every upgrading package must be included.
                for prv in pkg.provides:
                    for upg in prv.upgradedby:
                        for upgpkg in upg.packages:
                            if (subset.get(upgpkg) is not INSTALL and
                                set.get(upgpkg) is INSTALL):
                                if upgpkg in locked:
                                    raise Error, "Package '%s' is locked" % \
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
            raise Error, "Package '%s' is locked" % pkg

        locked[pkg] = True

        if pkg not in set:
            raise Error, "Package '%s' is not in changeset" % pkg
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
                                    raise Error, "Package '%s' is locked" % \
                                                 prvpkg
                                self.exclude(changeset, prvpkg, locked)

            elif op is REMOVE:

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
                            raise Error, "Package '%s' is locked" % cnfpkg
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

def sortUpgrades(pkgs, policy=None):
    upgpkgs = {}
    for pkg in pkgs:
        dct = {}
        rupg = recursiveUpgrades(pkg, dct)
        del dct[pkg]
        upgpkgs[pkg] = dct
    pkgs.sort()
    pkgs.reverse()
    newpkgs = []
    priority = {}
    if policy:
        for pkg in pkgs:
            priority[pkg] = policy.getPriority(pkg)
    else:
        for pkg in pkgs:
            priority[pkg] = pkg.getPriority()
    for pkg in pkgs:
        pkgupgs = upgpkgs[pkg]
        for i in range(len(newpkgs)):
            newpkg = newpkgs[i]
            if newpkg in pkgupgs or priority[pkg] > priority[newpkg]:
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

def sortInternalRequires(pkgs):
    rellst = []
    numrel = {}
    pkgmap = dict.fromkeys(pkgs, True)
    for pkg in pkgs:
        rellst.append((recursiveInternalRequires(pkgmap, pkg, numrel), pkg))
    rellst.sort()
    rellst.reverse()
    pkgs[:] = [x[1] for x in rellst]

def recursiveInternalRequires(pkgmap, pkg, numrel, done=None):
    if done is None:
        done = {}
    done[pkg] = True
    if pkg in numrel:
        return numrel[pkg]
    n = 0
    for prv in pkg.provides:
        for req in prv.requiredby:
            for relpkg in req.packages:
                if relpkg in pkgmap and relpkg not in done:
                    n += 1
                    if relpkg in numrel:
                        n += numrel[relpkg]
                    else:
                        n += recursiveInternalRequires(pkgmap, relpkg,
                                                       numrel, done)
    numrel[pkg] = n
    return n

try:
    import psyco
except ImportError:
    pass
else:
    psyco.bind(Transaction)

# vim:ts=4:sw=4:et

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
from smart.const import INSTALL, REMOVE, UPGRADE, FIX, REINSTALL, KEEP
from smart.cache import PreRequires, Package
from smart import *
from math import atan, pi
from heapq import heappush, heappop

#==========================================================
# Algorithm tweaks

earlyAbort = 1
# If 1, we stop the evaluation of alternatives whenever we found a feasible
# one and all remaining alternatives have a lower package priorities
# (this is a local decision, before exploring the consequences).
# If 0 (old behavior), we exhaust all possibilities.

pruneByWeight = 1
# If 1, we remember the best alternative found so far (in terms of changeset
# weight) and prune the search tree when better alternatives are not possible.
# This makes some monotonicity assumptions on the policy-determined changeset
# weights, which are not strictly true, so the policy enforcement might not be
# perfect; but the computation is much faster.
# If 0 (old behavior), no such pruning is done.

immediateUpdown = 1
# If 1, when we have to remove a package due to dependencies we immediately
# look for an up/downgrade replacement. In conjunction with earlyAbort=1,
# this means broken dependencies will be removed only as a last resort
# (i.e., if it's impossible to preserve them by up/downgrdading)
# regardless of the changeset weights given by the policy.
# This also tends to produce changesets with fewer Removes and more Upgrades.
# If 0 (old behavior), we instead create a pending task and delay it for 
# later; this tends to cause huge remove cascades and, consequentially,
# slower running and larger changesets. However, it fully respects the
# policy weights and explors more options.

forkSearch = 1
# If 1, whenever there are multiple alternatives to explore this will be
# tries in parallel using the A* search algorithm; this allows us to
# find a feasible alternative quickly and, in conjunction with
# pruneByWeight=1, finish the computation quickly.
# If 0, we don't do that.

prioritiesAffectWeight = 1
# If 1, the magnitude of package priorities affect the magnitude changeset
# weights, so (for example) a huge priority means "do whatever it takes to
# get this package". This affects only the top-level packages of "upgrade"
# commands; the rest are handled as below.
# If 0 (old behavior), package priorities are used only to determine boolean
# upgrade relations, and each such relation has a constant effect on
# changeset weights.

priorityScale = 5
# Value of a typical "moderate" package priority, for scaling. If very different
# from what the user uses, the importance of package priorities may be
# overestimated or underestimated by some policies.

#==========================================================
# Debugging

# Debug trace verbosity level, 0 for silence.
traceVerbosity = 0

# Max recursion level to trace
# (At large depths, running time is dominated by trace I/O.)
traceDepth = 5

#==========================================================

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
        if state is not self:
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

    def set(self, pkg, op, force=False):
        if self.get(pkg) is op:
            return
        if op is INSTALL:
            if force or not pkg.installed:
                self[pkg] = INSTALL
            else:
                if pkg in self:
                    del self[pkg]
        else:
            if force or pkg.installed:
                self[pkg] = REMOVE
            else:
                if pkg in self:
                    del self[pkg]

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
        for pkg in pkgconf.filterByFlag("lock", cache.getPackages()):
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

    def getBestUpdownDeltaWeight(self, pkg):
        """
        Return the best possible change in weight when pkg is up/downgraded or removed.
        """
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
            set[pkg] = -(set[pkg] - lower)*10
        return set


class PolicyWithPriorities(Policy):
    def runStarting(self):
        Policy.runStarting(self)
        self._upgrading = upgrading = {}
            # upgrading[x][y] is the (possibly negative) priority advantage of
            # x over y, or -/+0.5 if x and y have the same package priority but
            # an upgrade relation exists between them.
            # Positive means x upgrades y.
        self._upgraded = upgraded = {}
        self._downgraded = downgraded = {}
        self._bestdeltapri = bestdeltapri = {}
            # self._bestdeltapri[x] is max(pri(y)-pri(x)) over all y up/downgrading x
        self._sortbonus = sortbonus = {}
        self._stablebonus = stablebonus = {}
        self._bestUpdownDeltaWeight = {}  # cache of getBestUpdownDeltaWeight()
        queue = self._trans.getQueue()
        for pkg in self._trans.getCache().getPackages():
            # Precompute upgrade relations.
            for upg in pkg.upgrades:
                for prv in upg.providedby:
                    for prvpkg in prv.packages:
                        if prvpkg.installed:
                            deltapri = self.getPriority(pkg) - self.getPriority(prvpkg)
                            if deltapri==0:
                                deltapri = 0.5
                            dct = upgrading.get(pkg)
                            if dct:
                                dct[prvpkg] = deltapri
                            else:
                                upgrading[pkg] = {prvpkg: deltapri}
                            if deltapri>0:
                                lst = upgraded.get(prvpkg)
                                if lst:
                                    lst.append(pkg)
                                else:
                                    upgraded[prvpkg] = [pkg]
                            else:
                                lst = downgraded.get(prvpkg)
                                if lst:
                                    lst.append(pkg)
                                else:
                                    downgraded[prvpkg] = [pkg]
                            if prvpkg not in bestdeltapri or bestdeltapri[prvpkg]<deltapri:
                                 bestdeltapri[prvpkg] = deltapri
            # Downgrades are upgrades if they have a higher package priority.
            for prv in pkg.provides:
                for upg in prv.upgradedby:
                    for upgpkg in upg.packages:
                        if upgpkg.installed:
                            deltapri = self.getPriority(pkg) - self.getPriority(upgpkg)
                            if deltapri==0:
                                deltapri = -0.5
                            dct = upgrading.get(pkg)
                            if dct:
                                dct[upgpkg] = deltapri
                            else:
                                upgrading[pkg] = {upgpkg: deltapri}
                            if deltapri>0:
                                lst = upgraded.get(upgpkg)
                                if lst:
                                    lst.append(pkg)
                                else:
                                    upgraded[upgpkg] = [pkg]
                            else:
                                lst = downgraded.get(upgpkg)
                                if lst:
                                    lst.append(pkg)
                                else:
                                    downgraded[upgpkg] = [pkg]
                            if upgpkg not in bestdeltapri or bestdeltapri[upgpkg]<deltapri:
                                 bestdeltapri[upgpkg] = deltapri

        # If package A-2.0 upgrades package A-1.0, and package A-2.0 is
        # upgraded by A-3.0, give a bonus if A-1.0 is upgraded without
        # installing A-2.0. In practice, this is a little bit more
        # complex since there might be multiple levels of upgrades, and
        # we can't penalize a possible package A2-2.0 which upgrades
        # A-1.0 as well, and is not upgraded by anyone else.
        for bonuspkg in upgraded:
            upgmap = dict.fromkeys(upgraded[bonuspkg])
            sb = {}
            bonusvalue = {}
            bonusdeps = {}
            queue = [[bonuspkg]]
            while queue:
                path = queue.pop(0)
                pathlen = len(path)
                pkg = path[-1]
                for prv in pkg.provides:
                    for upg in prv.upgradedby:
                        for upgpkg in upg.packages:
                            if (not upgpkg.installed and
                                upgpkg in upgmap and upgpkg not in path and
                                self.getPriority(pkg) <=
                                self.getPriority(upgpkg)):
                                if pathlen > 1:
                                    # Paths always increase in size, so we can
                                    # be sure that the value being introduced
                                    # here is >= to the previous one.
                                    bonusvalue[pkg] = -30*(pathlen-1)
                                    deps = bonusdeps.setdefault(pkg, {})
                                    for pathpkg in path[1:]:
                                        deps[pathpkg] = True
                                queue.append(path+[upgpkg])
                for upg in pkg.upgrades:
                    for prv in upg.providedby:
                        for prvpkg in prv.packages:
                            if (not prvpkg.installed and
                                prvpkg in upgmap and prvpkg not in path and
                                self.getPriority(pkg) <
                                self.getPriority(prvpkg)):
                                if pathlen > 1:
                                    bonusvalue[pkg] = -30*(pathlen-1)
                                    deps = bonusdeps.setdefault(pkg, {})
                                    for pathpkg in path[1:-1]:
                                        deps[pathpkg] = True
                                queue.append(path+[prvpkg])
            if bonusvalue:
                lst = [(bonusvalue[pkg], bonusdeps[pkg]) for pkg in bonusvalue]
                lst.sort()
                stablebonus[bonuspkg] = lst

        pkgs = self._trans._queue.keys()
        sortUpgrades(pkgs, self)
        for i, pkg in enumerate(pkgs):
            self._sortbonus[pkg] = -1./(i+100)

    def runFinished(self):
        Policy.runFinished(self)
        del self._upgrading
        del self._upgraded
        del self._downgraded
        del self._bestdeltapri
        del self._bestUpdownDeltaWeight

    def _deltaWeightByDeltaPri(self, deltapri):
        """Return weight delta for up/downgrading a pair of packages with the given priority delta"""
        return 0

    def _deltaWeightForRemove(self, pri):
        """Return the weight delta for removing (not up/downgrading) a package with the given priority"""
        return 0

    def _calcStableBonus(self, pkg, changeset):
        return 0

    def getWeight(self, changeset):
        weight = 0
        upgrading = self._upgrading
        upgraded = self._upgraded
        downgraded = self._downgraded
        sortbonus = self._sortbonus

        upgradedmap = {}
        for pkg in changeset:
            if changeset[pkg] is REMOVE:
                # Up/downgrading a package that will be removed
                # is better than upgrading a package that will
                # stay in the system.
                for upgpkg in upgraded.get(pkg, ()):
                    if changeset.get(upgpkg) is INSTALL:
                        weight += self._rewardRemoveUpgraded # Upgraded
                        break
                else:
                    for dwnpkg in downgraded.get(pkg, ()):
                        if changeset.get(dwnpkg) is INSTALL:
                            weight += self._rewardRemovedDowngraded # Downgraded
                            break
                    else: # Removed and not replaced by up/downgrade
                        weight += self._deltaWeightForRemove(self.getPriority(pkg))
            else: # INSTALL
                upgpkgs = upgrading.get(pkg)
                if upgpkgs:
                    weight += sortbonus.get(pkg, 0)
                    for upgpkg in upgpkgs:
                        deltapri = upgpkgs[upgpkg]
                        if upgradedmap.has_key(upgpkg):
                             upgradedmap[upgpkg] = max(deltapri,upgradedmap[upgpkg])
                        else:
                             upgradedmap[upgpkg] = deltapri
                else:
                    weight += self._rewardInstallNotUpdown # Install not up/downgrading anything

        # Contribution from up/downgrading packages:
        for pkg in upgradedmap:
            weight += self._calcStableBonus(pkg, changeset)
            deltapri = upgradedmap[pkg]
            weight += self._deltaWeightByDeltaPri(deltapri)

        return weight

    def getBestUpdownDeltaWeight(self, pkg):
        weight = self._bestUpdownDeltaWeight.get(pkg);
        if weight is not None:
            return weight

        bestdeltapri = self._bestdeltapri
        upgraded = self._upgraded
        weight = 0
        # Best imaginable upgrade?
        if pkg in bestdeltapri:
            deltapri = bestdeltapri[pkg]
            weight = self._deltaWeightByDeltaPri(deltapri)
            weight += self._rewardRemoveUpgraded # for removing old
        # We could also just remove it
        weight = min(weight, self._deltaWeightForRemove(self.getPriority(pkg)))

        self._bestUpdownDeltaWeight[pkg] = weight
        return weight

class PolicyInstall(PolicyWithPriorities):
    """Give precedence for keeping functionality in the system."""

    _rewardRemoveUpgraded = -1
    _rewardRemovedDowngraded = 15
    _rewardInstallNotUpdown = 3

    def _deltaWeightByDeltaPri(self, deltapri):
        if not prioritiesAffectWeight:
            return deltapri>0 and 2 or 0
        # Bounded effect of priorities, so that num. affected packages maintains its importance.
        # The +/-0.5 is for up/downgrades with no priority difference.
        assert(abs(deltapri)>=0.5)
        if deltapri>=0:
            return 2.5 - 1*atan((deltapri-0.5)/priorityScale)/(pi/2) # (1.5,2.5]
        else:
            return 3 - 2*atan((deltapri+0.5)/priorityScale)/(pi/2) # [3,5)

    def _deltaWeightForRemove(self, pri):
        if not prioritiesAffectWeight:
            return 20
        # Bounded effect of priorities, so that num. affected packages maintains its importance.
        if pri>=0:
            return 20 + 10*atan(pri/priorityScale)/(pi/2) # [20,30)
        else:
            return 20 + 4*atan(1.0*pri/priorityScale)/(pi/2) # (16,20]

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

class PolicyUpgrade(PolicyWithPriorities):
    """Give precedence to the choice with more upgrades and smaller impact."""

    _rewardRemoveUpgraded = -1
    _rewardRemovedDowngraded = 0
    _rewardInstallNotUpdown = 1

    def _deltaWeightByDeltaPri(self, deltapri):
        if not prioritiesAffectWeight:
            return deltapri>0 and -30 or 0
        # Unbounded so we can express "get me that version whatever it takes".
        # The +/-0.5 is for up/downgrades with no priority difference.
        assert(abs(deltapri)>=0.5)
        if deltapri>=0:
            return -30 - 10*(deltapri-0.5)/priorityScale # (-infty,-30]
        else:
            return 1 - 10*(deltapri+0.5)/priorityScale # [1,infty)

    def _deltaWeightForRemove(self, pri):
        if not prioritiesAffectWeight:
            return 3
        # Penalty for removing high-priority packages is unbounded,
        # to let us express "get me that version whatever it takes".
        # For negative priorities we bound up from 0, so we're never happy
        # to remove a package (but still prioritize by weight).
        if pri>=0:
            return 10 + 10.0*pri/priorityScale # [10,infty)
        else:
            return 10 + 5*atan(1.0*pri/priorityScale)/(pi/2) # (5,10]

    def _calcStableBonus(self, pkg, changeset):
        weight = 0
        stablebonus = self._stablebonus
        sb = stablebonus.get(pkg)
        if sb:
            for bonusvalue, bonusdeps in sb:
                for deppkg in bonusdeps:
                    if deppkg in changeset:
                        break
                else:
                    weight += bonusvalue
                    break
        return weight


class Failed(Error): pass
class Prune(Error): pass

PENDING_REMOVE   = 1
PENDING_INSTALL  = 2
PENDING_UPDOWN   = 3

WEIGHT_NONE   = 1e100   # float to make min() "%f" work, but larger than any real weight

class Transaction(object):
    def __init__(self, cache, policy=None, changeset=None, queue=None):
        self._cache = cache
        self._policy = policy and policy(self) or Policy(self)
        self._changeset = changeset or ChangeSet(cache)
        self._queue = queue or {}
        self._necessarypkgs = {} # A in _necessarypkgs[B] means it's impossible to install A without B
        self._necessitatespkgs = {} # A in _necessitatespkgs[B] means it's impossible to install B without A
        self._prohibitspkgs = {} # A in _prohibitpkgs[B] means it's impossible to install A and B

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

    class Task(object):
        """
        This class provides an iterator (to be implemented by a generator function).
        The calls to next() return a series of tentative changesets weights, which are
        (hopefully, but not necessarily) monotonically increasing.
        When the final changeset is ready, next() raises StopIteration, and _changeset
        and _locked have their final value.
        """ 
        def __init__(self, parent, gen, changeset, locked, pruneweight, yieldweight, csweight, pri, order, desc):
            self._parent =  parent          # Parent task (a Task or RootTask object)
            self._changeset = changeset     # (Tentative) changeset
            self._locked = locked           # (Tentative) locked
            self._csweight = csweight       # (Tentative) changeset weight, primary sort key
            self._pri = pri                 # Priority, secondary sort key
            self._order = order             # Tertiary sort key for determinism (and trace output)
            self._gen = gen                 # the generator function
            self._desc = desc               # Description for trace output
            self._pruneweight = pruneweight # Weight at which to raise Prune
            self._yieldweight = yieldweight # Weight at which to yield execution
            self._trans = parent._trans     # the Transaction object we belong to
            self._depth = parent._depth + 1 # Trace depth level
            self._tracepath = "%s-%d" % (parent._tracepath, order)

        def setWeights(self, pruneweight, yieldweight):
            self._pruneweight = pruneweight
            self._yieldweight = yieldweight

        def getChangesetWeight(self):
            if self._csweight == WEIGHT_NONE:
                self._csweight = self._trans.getPolicy().getWeight(self._changeset)
            return self._csweight

        def next(self):
            self._csweight = WEIGHT_NONE   # in case _gen raises StopIteration without recomputing
            self._csweight = self._gen.next()
            return self._csweight

        def trace(self, verbosity, str, args=[], cs=None):
            """
            pretty-print a trace line if it patches the current filter.
            It accepts format arguments and evaluates them only if needed, instead
            of having the caller always evaluate its % operator.
            """
            if verbosity<=traceVerbosity and self._depth<=traceDepth:
                print "%s>     %s" % (self._tracepath, str % args)
                if traceVerbosity>6 and cs is not None:
                    print "--> changeset:\n%s" % (cs)

        def __iter__(self):
            return self;

        def __cmp__(self,other):
            return cmp( (self._csweight, self._pri, self._order), (other._csweight, self._pri, other._order) )

    class RootTask(object):
        def __init__(self, trans):
            self._trans = trans
            self._depth = 0
            self._order = 0
            self._tracepath = '#'

    class TaskInstall(Task):
      def __init__(self, parent, pkg, changeset, locked, pending, pruneweight, yieldweight, csweight=WEIGHT_NONE, pri=0, order=0, desc=""):
        gen = self._install(pkg, pending)
        parent._trans.Task.__init__(self, parent, gen, changeset, locked, pruneweight, yieldweight, csweight, pri, order, desc)

      def _install(self, pkg, pending):
        trans = self._trans
        changeset = self._changeset
        locked = self._locked
        depth = self._depth
        self.trace(1,  "_install(%s, pw=%f, yw=%f)", (pkg, self._pruneweight, self._yieldweight))

        ownpending = pending is None
        if ownpending:
            pending = []

        locked[pkg] = True
        changeset.set(pkg, INSTALL)
        isinst = changeset.installed
        if pruneByWeight:
            # Find an lower bound on the weight resulting from this install, and prune.
            optweight = None
            for prhpkg in trans.getProhibits(pkg):
                if isinst(prhpkg):
                    if optweight is None:
                        optweight = trans.getPolicy().getWeight(changeset)
                    optweight += trans.getPolicy().getBestUpdownDeltaWeight(prhpkg)
            if optweight is not None:
                if optweight > self._pruneweight:
                    self.trace(2, "pruned _install")
                    raise Prune, _("Pruned installation of %s") % (pkg)
                elif forkSearch and optweight>=self._yieldweight:
                    self. trace(2, "yielding (ow=%f)", optweight)
                    yield optweight

        # Remove packages conflicted by this one.
        for cnf in pkg.conflicts:
            for prv in cnf.providedby:
                for prvpkg in prv.packages:
                    if prvpkg is pkg:
                        continue
                    if not isinst(prvpkg):
                        locked[prvpkg] = True
                        continue
                    if prvpkg in locked:
                        raise Failed, _("Can't install %s: conflicted package "
                                        "%s is locked") % (pkg, prvpkg)
                    if immediateUpdown:
                        task = trans.TaskUpdown(self, prvpkg, changeset, locked, self._pruneweight, self._yieldweight, force=1)
                        for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)
                    else:
                        task = trans.TaskRemove(self, prvpkg, changeset, locked, pending, self._pruneweight, self._yieldweight)
                        for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)
                        pending.append((PENDING_UPDOWN, prvpkg))

        # Remove packages conflicting with this one.
        for prv in pkg.provides:
            for cnf in prv.conflictedby:
                for cnfpkg in cnf.packages:
                    if cnfpkg is pkg:
                        continue
                    if not isinst(cnfpkg):
                        locked[cnfpkg] = True
                        continue
                    if cnfpkg in locked:
                        raise Failed, _("Can't install %s: it's conflicted by "
                                        "the locked package %s") \
                                      % (pkg, cnfpkg)
                    if immediateUpdown:
                        task = trans.TaskUpdown(self, cnfpkg, changeset, locked, self._pruneweight, self._yieldweight, force=1)
                        for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)
                    else:
                        task = trans.TaskRemove(self, cnfpkg, changeset, locked, pending, self._pruneweight, self._yieldweight)
                        for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)
                        pending.append((PENDING_UPDOWN, cnfpkg))

        # Remove packages with the same name that can't
        # coexist with this one.
        namepkgs = trans.getCache().getPackages(pkg.name)
        for namepkg in namepkgs:
            if namepkg is not pkg and not pkg.coexists(namepkg):
                if not isinst(namepkg):
                    locked[namepkg] = True
                    continue
                if namepkg in locked:
                    raise Failed, _("Can't install %s: it can't coexist "
                                    "with %s") % (pkg, namepkg)
                task = trans.TaskRemove(self, namepkg, changeset, locked, pending, self._pruneweight, self._yieldweight)
                for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)

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
                raise Failed, _("Can't install %s: no package provides %s") % \
                              (pkg, req)

            if len(prvpkgs) == 1:
                # Don't check locked here. prvpkgs was
                # already filtered above.
                task = trans.TaskInstall(self, prvpkgs.popitem()[0], changeset, locked, pending, self._pruneweight, self._yieldweight)
                for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)
            else:
                # More than one package provide it. This package
                # must be post-processed.
                pending.append((PENDING_INSTALL, pkg, req, prvpkgs.keys()))

        if ownpending:
            task = trans.TaskPending(self, changeset, locked, pending, self._pruneweight, self._yieldweight)
            for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)

    class TaskRemove(Task):
      def __init__(self, parent, pkg, changeset, locked, pending, pruneweight, yieldweight, csweight=WEIGHT_NONE, pri=0, order=0, desc=""):
        gen = self._remove(pkg, pending)
        parent._trans.Task.__init__(self, parent, gen, changeset, locked, pruneweight, yieldweight, csweight, pri, order, desc)

      def _remove(self, pkg, pending):
        trans = self._trans
        changeset = self._changeset
        locked = self._locked
        depth = self._depth
        pruneweight = self._pruneweight
        self.trace(1, "_remove(%s, pw=%f, yw=%f)", (pkg, self._pruneweight, self._yieldweight))

        if pkg.essential:
            raise Failed, _("Can't remove %s: it's an essential package")
        isinst = changeset.installed

        ownpending = pending is None
        if ownpending:
            pending = []

        locked[pkg] = True
        changeset.set(pkg, REMOVE)

        if pruneByWeight and immediateUpdown:
            # Find a lower bound on the weight resulting from this remove, and prune.
            # We're ignoring the possibility that pkg will be upgraded rather than
            # removed, because immediateUpdown doesn't remove if updown is possible.
            # We're ignoring the possibility that upgrades which are not *staticially*
            # necessary will *improve* the weight, because that's hard to handle
            # and probably not very common.
            optweight = trans.getPolicy().getWeight(changeset)
            for necpkg in trans.getNecessary(pkg):
                if isinst(necpkg):
                    optweight += trans.getPolicy().getBestUpdownDeltaWeight(necpkg)
            if optweight > pruneweight:
                self.trace(2, "pruned _remove (ow=%f > pw=%f)", (optweight, pruneweight))
                raise Prune, _("Pruned removal of %s") % (pkg)
            elif forkSearch and optweight>=self._yieldweight:
                self.trace(2, "yielding (ow=%f)", optweight)
                yield optweight
                pruneweight=min(pruneweight,self._pruneweight)

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
                            raise Failed, _("Can't remove %s: %s is locked") \
                                          % (pkg, reqpkg)
                        if immediateUpdown:
                            task = trans.TaskUpdown(self, reqpkg, changeset, locked, pruneweight, self._yieldweight, force=1)
                            for res in task: yield res; pruneweight=min(pruneweight,self._pruneweight); task.setWeights(pruneweight, self._yieldweight)
                        else:
                            task = trans.TaskRemove(self, reqpkg, changeset, locked, pending, pruneweight, self._yieldweight)
                            for res in task: yield res; pruneweight=min(pruneweight,self._pruneweight); task.setWeights(pruneweight, self._yieldweight)
                            pending.append((PENDING_UPDOWN, reqpkg))

        if ownpending:
            task = trans.TaskPending(self, changeset, locked, pending, pruneweight, self._yieldweight)
            for res in task: yield res; pruneweight=min(pruneweight,self._pruneweight); task.setWeights(pruneweight, self._yieldweight)

    class TaskUpdown(Task):
      def __init__(self, parent, pkg, changeset, locked, pruneweight, yieldweight, force, csweight=WEIGHT_NONE, pri=0, order=0, desc=""):
        """
        If force=1, insists on replacing or removing pkg.
        """
        gen = self._updown(pkg, force)
        parent._trans.Task.__init__(self, parent, gen, changeset, locked, pruneweight, yieldweight, csweight, pri, order, desc)

      def _updown(self, pkg, force):
        trans = self._trans
        changeset = self._changeset
        locked = self._locked
        depth = self._depth
        pruneweight = self._pruneweight
        self.trace(1, "_updown(%s, pw=%f, yw=%f, f=%d)", (pkg, pruneweight, self._yieldweight, force))

        isinst = changeset.installed
        getpriority = trans.getPolicy().getPriority

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
        taskheap = []
        doneheap = []
        order = 1
        getweight = trans.getPolicy().getWeight
        csweight = getweight(changeset)
        if not force:
            pruneweight = min(pruneweight, csweight)

        # Create tasks for upgrading options
        upgpkgs = upgpkgs.keys()
        sortUpgrades(upgpkgs)
        for upgpkg in upgpkgs:
            cs = changeset.copy()
            lk = locked.copy()
            task = trans.TaskInstall(self, upgpkg, cs, lk, None, pruneweight, self._yieldweight,
                                     csweight, 0, order, "upgrade to %s" % upgpkg)
            heappush(taskheap, task) 
            order += 1

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
            # Create tasks for downgrading options
            # XXX We should have a prune/yield point when other options have been ruled out
            dwnpkgs = dwnpkgs.keys()
            sortUpgrades(dwnpkgs)
            for dwnpkg in dwnpkgs:
                cs = changeset.copy()
                lk = locked.copy()
                task = trans.TaskInstall(self, dwnpkg, cs, lk, None, pruneweight, self._yieldweight,
                                         csweight, 1, order, "downgrade to %s" % dwnpkg)
                heappush(taskheap, task) 
                order += 1

        # If forced, create a task for simply removing the package
        if force:
            cs = changeset.copy()
            lk = locked.copy()
            task = trans.TaskRemove(self, pkg, cs, lk, None, pruneweight, self._yieldweight,
                                    csweight, 2, order, "remove")
            heappush(taskheap, task)

        # Execute the tasks to compute feasible alternatives
        while len(taskheap)>0:
            task = heappop(taskheap)
            yw = min(self._yieldweight, pruneweight)
            if len(taskheap)>1:
                yw = min(yw, taskheap[1].getChangesetWeight())
            try:
                task.setWeights(pruneweight, yw)
                res = task.next()
            except Failed:
                pass
            except Prune:
                pass
            except StopIteration:  # the task has finished
                cs = task._changeset
                csw = task.getChangesetWeight()
                self.trace(3, "feasible _updown alternative for %s: %s (csw=%f)", (pkg, task._desc, csw), cs)
                heappush(doneheap, task)
                pruneweight = min(pruneweight, csw)
            else:
                yield res
                pruneweight = min(pruneweight, self._pruneweight)
                heappush(taskheap, task)

        if force:
            if len(doneheap)==0:
                raise Failed, _("Can't get rid of %s" % pkg)
        else:
            if doneheap[0].getChangesetWeight() >= csweight:
                self._csweight = csweight
                return
        self._changeset.setState(doneheap[0]._changeset)
        self._csweight = (doneheap[0].getChangesetWeight())

    class TaskPending(Task):
      def __init__(self, parent, changeset, locked, pending, pruneweight, yieldweight, csweight=WEIGHT_NONE, pri=0, order=0, desc=""):
        gen = self._pending(pending)
        parent._trans.Task.__init__(self, parent, gen, changeset, locked, pruneweight, yieldweight, csweight, pri, order, desc)

      def _pending(self, pending):
        trans = self._trans
        changeset = self._changeset
        locked = self._locked
        depth = self._depth
        if traceVerbosity<4:
            self.trace(1, "_pending(pw=%f, yw=%f)", (self._pruneweight, self._yieldweight))
        else:
            self.trace(4, "_pending(%s, pw=%f, yw=%f)", (pending, self._pruneweight, self._yieldweight))

        isinst = changeset.installed
        getweight = trans.getPolicy().getWeight

        updown = []
        while pending:
            item = pending.pop(0)
            kind = item[0]
            if kind == PENDING_UPDOWN:
                kind, pkg = item
                self.trace(1, "_pending.PENDING_UPDOWN (%s)", (pkg) )
                updown.append(pkg)
            elif kind == PENDING_INSTALL:
                kind, pkg, req, prvpkgs = item
                self.trace(1, "_pending.PENDING_INSTALL (%s, %s, %s)", (pkg,req,prvpkgs) )

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
                    raise Failed, _("Can't install %s: no package "
                                    "provides %s") % (pkg, req)

                if len(prvpkgs) > 1:
                    # More than one package provide it. We use _pending here,
                    # since any option must consider the whole change for
                    # weighting.
                    alternatives = []
                    failures = []
                    sortUpgrades(prvpkgs)
                    keeporder = 0.000001
                    pw = trans.getPolicy().getPriorityWeights(prvpkgs)
                    _maxpw = None
                    _pruneweight = self._pruneweight
                    for prvpkg in prvpkgs:
                        if (earlyAbort and _maxpw is not None and
                            pw[prvpkg] > _maxpw):
                            self.trace(2, "early abort of PENDING_INSTALL at %s", (prvpkg))
                            continue # don't assume sort order
                        try:
                            cs = changeset.copy()
                            lk = locked.copy()
                            task = trans.TaskInstall(self, prvpkg, cs, lk, None, _pruneweight, self._yieldweight)
                            for res in task: yield res; _pruneweight=min(_pruneweight,self._pruneweight); task.setWeights(_pruneweight, self._yieldweight)
                        except Failed, e:
                            failures.append(unicode(e))
                        except Prune, e:
                            failures.append(unicode(e))
                        else:
                            csweight = getweight(cs)
                            self.trace(2, "feasible PENDING_INSTALL alternative: %s  (csw=%f)", (prvpkg, csweight), cs)
                            _pruneweight = min(_pruneweight, csweight)
                            alternatives.append((csweight+pw[prvpkg]+
                                                 keeporder, cs, lk))
                            keeporder += 0.000001
                            if earlyAbort:
                                _maxpw = pw[prvpkg]
                    if not alternatives:
                        raise Failed, _("Can't install %s: all packages "
                                        "providing %s failed to install:\n%s")\
                                      % (pkg, req,  "\n".join(failures))
                    alternatives.sort()
                    changeset.setState(alternatives[0][1])
                    if len(alternatives) == 1:
                        locked.update(alternatives[0][2])
                else:
                    # This turned out to be the only way.
                    task = trans.TaskInstall(self, prvpkgs[0], changeset, locked, pending, self._pruneweight, self._yieldweight)
                    for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)

            elif kind == PENDING_REMOVE:
                kind, pkg, prv, reqpkgs, prvpkgs = item
                self.trace(1, "_pending.PENDING_REMOVE (%s, %s, %s, %s)", (pkg, prv, reqpkgs, prvpkgs) )

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

                    if earlyAbort:
                        sortUpgrades(prvpkgs)
                        _maxpw = None
                    _pruneweight = self._pruneweight
                    pw = trans.getPolicy().getPriorityWeights(prvpkgs)
                    for prvpkg in prvpkgs:
                        if (earlyAbort and _maxpw is not None and
                            pw[prvpkg] > _maxpw):
                            self.trace(2, "early abort of PENDING_REMOVE at %s", (prvpkg))
                            continue # don't assume sort order
                        try:
                            cs = changeset.copy()
                            lk = locked.copy()
                            task = trans.TaskInstall(self, prvpkg, cs, lk, None, _pruneweight, self._yieldweight)
                            for res in task: yield res; _pruneweight=min(_pruneweight,self._pruneweight); task.setWeights(_pruneweight, self._yieldweight)
                        except Failed, e:
                            failures.append(unicode(e))
                        except Prune, e:
                            failures.append(unicode(e))
                        else:
                            csweight = getweight(cs)
                            self.trace(3, "feasible PENDING_REMOVE prv alternative: %s  (csw=%f)", (prvpkg, csweight), cs)
                            alternatives.append((csweight+pw[prvpkg],
                                                cs, lk))
                            _pruneweight = min(_pruneweight, csweight)
                            if earlyAbort:
                                _maxpw = pw[prvpkg]

                if not prvpkgs or not alternatives:

                    # There's no alternatives. We must remove
                    # every requiring package.

                    for reqpkg in reqpkgs:
                        if reqpkg in locked and isinst(reqpkg):
                            raise Failed, _("Can't remove %s: requiring "
                                            "package %s is locked") % \
                                          (pkg, reqpkg)
                    for reqpkg in reqpkgs:
                        # We check again, since other actions may have
                        # changed their state.
                        if not isinst(reqpkg):
                            continue
                        if reqpkg in locked:
                            raise Failed, _("Can't remove %s: requiring "
                                            "package %s is locked") % \
                                          (pkg, reqpkg)
                        if immediateUpdown:
                            task = trans.TaskUpdown(self, reqpkg, changeset, locked, self._pruneweight, self._yieldweight, force=1)
                            for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)
                        else:
                            task = trans.TaskRemove(self, reqpkg, changeset, locked, pending, self._pruneweight, self._yieldweight)
                            for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)
                    continue

                # Also try to remove every requiring package, or
                # upgrade/downgrade them to something which
                # does not require this dependency.
                if not (earlyAbort and immediateUpdown):
                    cs = changeset.copy()
                    lk = locked.copy()
                    try:
                        for reqpkg in reqpkgs:
                            if reqpkg in locked and isinst(reqpkg):
                                raise Failed, _("%s is locked") % reqpkg
                        for reqpkg in reqpkgs:
                            if not cs.installed(reqpkg):
                                continue
                            if reqpkg in lk:
                                raise Failed, _("%s is locked") % reqpkg
                            if immediateUpdown:
                                task = trans.TaskUpdown(self, reqpkg, cs, lk, _pruneweight, self._yieldweight, force=1)
                                for res in task: yield res; pruneweight=min(_pruneweight,self._pruneweight); task.setWeights(_pruneweight, self._yieldweight)
                            else:
                                task = trans.TaskRemove(self, reqpkg, cs, lk, None, pruneweight, self._yieldweight)
                                for res in task: yield res; pruneweight=min(_pruneweight,self._pruneweight); task.setWeights(_pruneweight, self._yieldweight)
                    except Failed, e:
                        failures.append(unicode(e))
                    except Prune, e:
                        failures.append(unicode(e))
                    else:
                        csweight = getweight(cs)
                        self.trace(3, "feasible PENDING_REMOVE remove alternative (csw=%f)", (csweight), cs)
                        alternatives.append((csweight, cs, lk))

                if not alternatives:
                    raise Failed, _("Can't install %s: all packages providing "
                                    "%s failed to install:\n%s") \
                                  % (pkg, prv,  "\n".join(failures))

                alternatives.sort()
                changeset.setState(alternatives[0][1])
                if len(alternatives) == 1:
                    locked.update(alternatives[0][2])

        for pkg in updown:
            self.trace(1, "_pending.final updown: %s", (pkg) )
            task = trans.TaskUpdown(self, pkg, changeset, locked, self._pruneweight, self._yieldweight, force=0)
            for res in task: yield res; task.setWeights(self._pruneweight, self._yieldweight)

        del pending[:]

    class TaskUpgrade(Task):
      def __init__(self, parent, pkgs, changeset, locked, pending, pruneweight, yieldweight, csweight=WEIGHT_NONE, pri=0, order=0, desc=""):
        gen = self._upgrade(pkgs, pending)
        parent._trans.Task.__init__(self, parent, gen, changeset, locked, pruneweight, yieldweight, csweight, pri, order, desc)

      def _upgrade(self, pkgs, pending):
        trans = self._trans
        changeset = self._changeset
        locked = self._locked
        depth = self._depth
        pruneweight = self._pruneweight
        self.trace(2, "_upgrade(%s)", (pkgs))

        isinst = changeset.installed
        getweight = trans.getPolicy().getWeight

        sortUpgrades(pkgs, trans.getPolicy())

        lockedstate = {}

        origchangeset = changeset.copy()

        weight = getweight(changeset)
        pruneweight = min(pruneweight, weight)
        for pkg in pkgs:
            self.trace(1, "_upgrade: add %s (pw=%f)", (pkg, pruneweight))
            if pkg in locked and not isinst(pkg):
                continue

            try:
                cs = changeset.copy()
                lk = locked.copy()
                task = trans.TaskInstall(self, pkg, cs, lk, None, self._pruneweight, self._yieldweight)
                for res in task: yield res; pruneweight=min(pruneweight,self._pruneweight); task.setWeights(pruneweight, self._yieldweight)
            except Failed, e:
                pass
            except Prune:
                pass
            else:
                lockedstate[pkg] = lk
                csweight = getweight(cs)
                if csweight < weight:
                    self.trace(2, "_upgrade added %s (csw=%f < w=%f)", (pkg, csweight, weight), cs)
                    weight = csweight
                    pruneweight = min(pruneweight, csweight)
                    changeset.setState(cs)
                else:
                    self.trace(3, "_upgrade not added %s (csw=%f >= w=%f)", (pkg, csweight, weight))

        lockedstates = {}
        for pkg in pkgs:
            if changeset.get(pkg) is INSTALL:
                state = lockedstate.get(pkg)
                if state:
                    lockedstates.update(state)

        # Can we beneficially undo some of the changes?
        for pkg in changeset.keys():

            op = changeset.get(pkg)
            if (op and op != origchangeset.get(pkg) and
                pkg not in locked and pkg not in lockedstates):
                self.trace(1, "_upgrade: undo %s %s", (op,pkg))

                try:
                    cs = changeset.copy()
                    lk = locked.copy()
                    if op is REMOVE:
                        task = trans.TaskInstall(self, pkg, cs, lk, None, pruneweight, self._yieldweight)
                        for res in task: yield res; pruneweight=min(pruneweight,self._pruneweight); task.setWeights(pruneweight, self._yieldweight)
                    elif op is INSTALL:
                        task = trans.TaskRemove(self, pkg, cs, lk, None, pruneweight, self._yieldweight)
                        for res in task: yield res; pruneweight=min(pruneweight,self._pruneweight); task.setWeights(pruneweight, self._yieldweight)
                except Failed, e:
                    pass
                except Prune:
                    pass
                else:
                    csweight = getweight(cs)
                    if csweight < weight:
                        self.trace(2, "_upgrade undid %s %s (csw=%f < w=%f)", (op, pkg, csweight, weight), cs)
                        weight = csweight
                        pruneweight = min(pruneweight, csweight)
                        changeset.setState(cs)
                    else:
                        self.trace(3, "_upgrade kept %s %s (csw=%f => w=%f)", (op, pkg, csweight, weight))

    class TaskFix(Task):
      def __init__(self, parent, pkgs, changeset, locked, pending, pruneweight, yieldweight, csweight=WEIGHT_NONE, pri=0, order=0, desc=""):
        gen = self._fix(pkgs, pending)
        parent._trans.Task.__init__(self, parent, gen, changeset, locked, pruneweight, yieldweight, csweight, pri, order, desc)

      def _fix(self, pkgs, pending):
        trans = self._trans
        changeset = self._changeset
        locked = self._locked
        depth = self._depth
        pruneweight = self._pruneweight
        self.trace(1, "_fix()")

        getweight = trans.getPolicy().getWeight
        isinst = changeset.installed

        sortUpgrades(pkgs)

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
                        iface.debug(_("Unsatisfied dependency: "
                                      "%s requires %s") % (pkg, req))
                        raise StopIteration
                for cnf in pkg.conflicts:
                    for prv in cnf.providedby:
                        for prvpkg in prv.packages:
                            if prvpkg is pkg:
                                continue
                            if isinst(prvpkg):
                                iface.debug(_("Unsatisfied dependency: "
                                              "%s conflicts with %s")
                                            % (pkg, prvpkg))
                                raise StopIteration
                for prv in pkg.provides:
                    for cnf in prv.conflictedby:
                        for cnfpkg in cnf.packages:
                            if cnfpkg is pkg:
                                continue
                            if isinst(cnfpkg):
                                iface.debug(_("Unsatisfied dependency: "
                                              "%s conflicts with %s")
                                            % (cnfpkg, pkg))
                                raise StopIteration
                # Check packages with the same name that can't
                # coexist with this one.
                namepkgs = trans.getCache().getPackages(pkg.name)
                for namepkg in namepkgs:
                    if (isinst(namepkg) and namepkg is not pkg
                        and not pkg.coexists(namepkg)):
                        iface.debug(_("Package %s can't coexist with %s") %
                                    (namepkg, pkg))
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
                task = trans.TaskInstall(self, pkg, cs, lk, None, pruneweight, self._yieldweight)
                for res in task: yield res; pruneweight=min(pruneweight,self._pruneweight); task.setWeights(pruneweight, self._yieldweight)
            except Failed, e:
                failures.append(unicode(e))
            except Prune, e:
                failures.append(unicode(e))
            else:
                # If they weight the same, it's better to keep the package.
                csweight = getweight(cs)
                self.trace(3, "feasible _fix install alternative (csw=%f)", (csweight), cs)
                alternatives.append((csweight-0.000001, cs))
                pruneweight = min(pruneweight, csweight)

            # Try to fix by removing it.
            try:
                cs = changeset.copy()
                lk = locked.copy()
                task = trans.TaskRemove(self, pkg, cs, lk, None, pruneweight, self._yieldweight)
                for res in task: yield res; pruneweight=min(pruneweight,self._pruneweight); task.setWeights(pruneweight, self._yieldweight)
                task = trans.TaskUpdown(self, pkg, cs, lk, pruneweight, self._yieldweight, force=0)
                for res in task: yield res; pruneweight=min(pruneweight,self._pruneweight); task.setWeights(pruneweight, self._yieldweight)
            except Failed, e:
                failures.append(unicode(e))
            except Prune, e:
                failures.append(unicode(e))
            else:
                csweight = getweight(cs)
                self.trace(3, "feasible _fix remove alternative (csw=%f)", (csweight), cs)
                alternatives.append((csweight, cs))
                pruneweight = min(pruneweight, csweight)

            if not alternatives:
                raise Failed, _("Can't fix %s:\n%s") % \
                              (pkg, "\n".join(failures))

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
            roottask = self.RootTask(self)
            pending = []

            for pkg in self._queue:
                op = self._queue[pkg]
                if op is KEEP:
                    if pkg in changeset:
                        del changeset[pkg]
                    locked[pkg] = True
                elif op is INSTALL:
                    if not isinst(pkg) and pkg in locked:
                        raise Failed, _("Can't install %s: it's locked") % pkg
                    changeset.set(pkg, INSTALL)
                    locked[pkg] = True
                elif op is REMOVE:
                    if isinst(pkg) and pkg in locked:
                        raise Failed, _("Can't remove %s: it's locked") % pkg
                    changeset.set(pkg, REMOVE)
                    locked[pkg] = True
                elif op is REINSTALL:
                    if pkg in locked:
                        raise Failed, _("Can't reinstall %s: it's locked")%pkg
                    changeset.set(pkg, INSTALL, force=True)
                    locked[pkg] = True
                elif op is UPGRADE:
                    pass

            upgpkgs = []
            fixpkgs = []
            for pkg in self._queue:
                op = self._queue[pkg]
                if op is KEEP:
                    if pkg.installed:
                        op = INSTALL
                    else:
                        op = REMOVE
                if op is INSTALL or op is REINSTALL:
                    task = self.TaskInstall(roottask, pkg, changeset, locked, pending, WEIGHT_NONE, WEIGHT_NONE)
                    for res in task: pass
                elif op is REMOVE:
                    task = self.TaskRemove(roottask, pkg, changeset, locked, pending, WEIGHT_NONE, WEIGHT_NONE)
                    for res in task: pass
                elif op is UPGRADE:
                    upgpkgs.append(pkg)
                elif op is FIX:
                    fixpkgs.append(pkg)

            if pending:
                task = self.TaskPending(roottask, changeset, locked, pending, WEIGHT_NONE, WEIGHT_NONE)
                for res in task: pass

            if upgpkgs:
                task = self.TaskUpgrade(roottask, upgpkgs, changeset, locked, pending, WEIGHT_NONE, WEIGHT_NONE)
                for res in task: pass

            if fixpkgs:
                task = self.TaskFix(roottask, fixpkgs, changeset, locked, pending, WEIGHT_NONE, WEIGHT_NONE)
                for res in task: pass

            self._changeset.setState(changeset)

        finally:
            self._queue.clear()
            self._policy.runFinished()

    def getNecessary(self, pkg, ignorepkgs={}):
        """
        Return the set of packages for which pkg is necessary (i.e., a chain of requires 
        with no alternatives).
        """

        if pkg in self._necessarypkgs:
            return self._necessarypkgs[pkg];
        necdct = {}

        # What requires pkg?
        for prv in pkg.provides:
            for req in prv.requiredby:
                # Is any other package providing req?
                for prv in req.providedby:
                   for prvpkg in prv.packages:
                       if prvpkg is not pkg:
                           break
                   else:
                       continue
                   break
                else:
                    # pkg is necessary for anyone requiring req:
                    for reqpkg in req.packages:
                        if reqpkg is not pkg and reqpkg not in necdct: 
                            necdct[reqpkg] = True

        # Recurse:
        save = True
        _ignorepkgs = ignorepkgs.copy()
        _ignorepkgs[pkg] = True
        for necpkg in necdct.keys():
            if necpkg not in ignorepkgs:
                necdct.update(self.getNecessary(necpkg, _ignorepkgs))
            else:
                save = False

        if save:
            self._necessarypkgs[pkg] = necdct;
            if traceVerbosity>=7: print "# getNecessary(%s) -> %s"  % (pkg, sorted(necdct.keys()))
        return necdct;

    def getNecessitates(self, pkg, ignorepkgs={}):
        """
        Return a set of packages which are necessary for pkg because they are
        the only way to satisfy requirements. The result is cached.
        """

        if pkg in self._necessitatespkgs:
            return self._necessitatespkgs[pkg];
        necdct = {}

        # What does prv require?
        for req in pkg.requires:
            # Is there a single package providing it?
            found = ()
            if len(req.providedby) != 1:
                break;
            for prv in req.providedby:
                if len(prv.packages) + len(found) > 1:
                    break;
                for prvpkg in prv.packages:
                    found=(prvpkg,)
            else:
                if len(found)==1:
                   # Yes, so pkg requires it.
                   necdct[found[0]] = True

        # Recurse:
        save = True
        _ignorepkgs = ignorepkgs.copy()
        _ignorepkgs[pkg] = True
        for necpkg in necdct.keys():
            if necpkg not in ignorepkgs:
                necdct.update(self.getNecessitates(necpkg, _ignorepkgs))
            else:
                save = False

        if save:
            self._necessitatespkgs[pkg] = necdct;
            if traceVerbosity>=7: print "# getNecessitates(%s) -> %s" % (pkg, sorted(necdct.keys()))
        return necdct;

    def getProhibits(self, pkg):
        """
        Return a set of packages which directly or indirectly conflict with pkg.
        We first construct a set of "red" packages, which must be installed if pkg
        is installed. We then identify all "blue" packages, which conflict with red
        packages. Then we find the closure of the "blue" packages by considering
        unsatisfiable requirements, and return this closure. The result is cached.
        """

        if pkg in self._prohibitspkgs:
            return self._prohibitspkgs[pkg];

        reds = self.getNecessitates(pkg)
        reds[pkg] = True
        blues = {}
        bluequeue = []

        # Direct conflicts of red packages:
        for redpkg in reds:
            for namepkg in self._cache.getPackages(redpkg.name):
                if namepkg not in reds and namepkg not in blues and not redpkg.coexists(namepkg):
                    blues[namepkg] = True
                    bluequeue.append(namepkg)
            for cnf in redpkg.conflicts:
                    for prv in cnf.providedby:
                        for prvpkg in prv.packages:
                            if prvpkg not in blues and prvpkg not in reds:
                                blues[prvpkg] = True
                                bluequeue.append(prvpkg)
            for prv in redpkg.provides:
                for cnf in prv.conflictedby:
                    for cnfpkg in cnf.packages:
                        if cnfpkg not in blues and cnfpkg not in reds:
                            blues[cnfpkg] = True
                            bluequeue.append(cnfpkg)

        # Indirect conflict due to necessary requirements of blue packages:
        while bluequeue:
            bluepkg = bluequeue.pop()
            # What requires bluepkg?
            for prv in bluepkg.provides:
                for req in prv.requiredby:
                    # Does any non-blue package provide that?
                    for prv in req.providedby:
                       for prvpkg in prv.packages:
                           if prvpkg not in blues:
                               break # provided by non-blue package
                       else:
                           continue
                       break
                    else: # all providing packages are blue
                        for reqpkg in req.packages:
                            if reqpkg not in blues and reqpkg not in reds:
                                blues[reqpkg] = True
                                bluequeue.append(reqpkg)

        self._prohibitspkgs[pkg] = blues;
        if traceVerbosity>=7: print "# getProhibits(%s) -> %s" % (pkg, sorted(blues.keys()))
        return blues;


class ChangeSetSplitter(object):
    # This class operates on *sane* changesets.

    DEBUG = 0

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

    def _remove(self, subset, pkg, locked):
        set = self._changeset

        # Include requiring packages being removed, or exclude
        # requiring packages being installed.
        for prv in pkg.provides:
            for req in prv.requiredby:

                reqpkgs = [reqpkg for reqpkg in req.packages if
                           subset.get(reqpkg) is INSTALL or
                           subset.get(reqpkg) is not REMOVE and
                           reqpkg.installed]

                if not reqpkgs:
                    continue

                # Check if some package that will stay
                # in the system or some package already
                # selected for installation provide the
                # needed dependency.
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
                    continue

                # Try to include some providing package
                # that is selected for installation.
                found = False
                for prv in req.providedby:
                    for prvpkg in prv.packages:
                        if (set.get(prvpkg) is INSTALL and
                            prvpkg not in locked):
                            try:
                                self.include(subset, prvpkg, locked)
                            except Error:
                                pass
                            else:
                                found = True
                                break
                    else:
                        continue
                    break
                if found:
                    continue

                # Now, try to keep in the system some
                # providing package which is already installed.
                found = False
                wasbroken = True
                for prv in req.providedby:
                    for prvpkg in prv.packages:
                        if set.get(prvpkg) is not REMOVE:
                            continue
                        wasbroken = False
                        # Package is necessarily in subset
                        # otherwise we wouldn't get here.
                        if prvpkg not in locked:
                            try:
                                self.exclude(subset, prvpkg, locked)
                            except Error:
                                pass
                            else:
                                found = True
                                break
                    else:
                        continue
                    break
                if found:
                    continue

                needed = (not wasbroken and 
                          (self._forcerequires or
                           isinstance(req, PreRequires)))

                for reqpkg in reqpkgs:

                    # Finally, try to exclude the requiring
                    # package if it is being installed, or
                    # include it if it's being removed.
                    reqpkgop = set.get(reqpkg)
                    if reqpkgop and reqpkg not in locked:
                        try:
                            if reqpkgop is INSTALL:
                                self.exclude(subset, reqpkg, locked)
                            else:
                                self.include(subset, reqpkg, locked)
                        except Error:
                            if needed: raise
                        else:
                            continue

                    # Should we care about this?
                    if needed:
                        raise Error, _("No providers for '%s', "
                                       "required by '%s'") % (req, reqpkg)

        # Check upgrading/downgrading packages.
        relpkgs = [upgpkg for prv in pkg.provides
                          for upg in prv.upgradedby
                          for upgpkg in upg.packages]
        relpkgs.extend([prvpkg for upg in pkg.upgrades
                               for prv in upg.providedby
                               for prvpkg in prv.packages])
        if set[pkg] is INSTALL:
            # Package is being installed, but excluded from the
            # subset. Exclude every related package which is
            # being removed.
            for relpkg in relpkgs:
                if subset.get(relpkg) is REMOVE:
                    if relpkg in locked:
                        raise Error, _("Package '%s' is locked") % relpkg
                    self.exclude(subset, relpkg, locked)
        else:
            # Package is being removed, and included in the
            # subset. Include every related package which is
            # being installed.
            for relpkg in relpkgs:
                if set.get(relpkg) is INSTALL and relpkg not in subset:
                    if relpkg in locked:
                        raise Error, _("Package '%s' is locked") % relpkg
                    self.include(subset, relpkg, locked)

    def _install(self, subset, pkg, locked):
        set = self._changeset

        # Check all dependencies needed by this package.
        for req in pkg.requires:

            # Check if any already installed or to be installed
            # package will solve the problem.
            found = False
            for prv in req.providedby:
                for prvpkg in prv.packages:
                    if (subset.get(prvpkg) is INSTALL or
                        (prvpkg.installed and
                         subset.get(prvpkg) is not REMOVE)):
                        found = True
                        break
                else:
                    continue
                break
            if found:
                continue

            # Check if any package that could be installed
            # may solve the problem.
            found = False
            for prv in req.providedby:
                for prvpkg in prv.packages:
                    if (set.get(prvpkg) is INSTALL
                        and prvpkg not in locked):
                        try:
                            self.include(subset, prvpkg, locked)
                        except Error:
                            pass
                        else:
                            found = True
                            break
                else:
                    continue
                break
            if found:
                continue

            # Nope. Let's try to keep in the system some
            # package providing the dependency.
            found = False
            wasbroken = True
            for prv in req.providedby:
                for prvpkg in prv.packages:
                    if set.get(prvpkg) is not REMOVE:
                        continue
                    wasbroken = False
                    # Package is necessarily in subset
                    # otherwise we wouldn't get here.
                    if prvpkg not in locked:
                        try:
                            self.exclude(subset, prvpkg, locked)
                        except Error:
                            pass
                        else:
                            found = True
                            break
                else:
                    continue
                break
            if found or wasbroken:
                continue

            # There are no solutions for the problem.
            # Should we really care about it?
            if (self._forcerequires or
                isinstance(req, PreRequires)):
                raise Error, _("No providers for '%s', "
                               "required by '%s'") % (req, pkg)

        cnfpkgs = [prvpkg for cnf in pkg.conflicts
                          for prv in cnf.providedby
                          for prvpkg in prv.packages
                           if prvpkg is not pkg]
        cnfpkgs.extend([cnfpkg for prv in pkg.provides
                               for cnf in prv.conflictedby
                               for cnfpkg in cnf.packages
                                if cnfpkg is not pkg])

        for cnfpkg in cnfpkgs:
            if (subset.get(cnfpkg) is INSTALL or
                cnfpkg.installed and subset.get(cnfpkg) is not REMOVE):
                if cnfpkg not in set:
                    raise Error, _("Can't remove %s, which conflicts with %s")\
                                 % (cnfpkg, pkg)
                if set[cnfpkg] is INSTALL:
                    self.exclude(subset, cnfpkg, locked)
                else:
                    self.include(subset, cnfpkg, locked)

        # Check upgrading/downgrading packages.
        relpkgs = [upgpkg for prv in pkg.provides
                          for upg in prv.upgradedby
                          for upgpkg in upg.packages]
        relpkgs.extend([prvpkg for upg in pkg.upgrades
                               for prv in upg.providedby
                               for prvpkg in prv.packages])
        if set[pkg] is INSTALL:
            # Package is being installed, and included in the
            # subset. Include every related package which is
            # being removed.
            for relpkg in relpkgs:
                if set.get(relpkg) is REMOVE and relpkg not in subset:
                    if relpkg in locked:
                        raise Error, _("Package '%s' is locked") % relpkg
                    self.include(subset, relpkg, locked)
        else:
            # Package is being removed, but excluded from the
            # subset. Exclude every related package which is
            # being installed.
            for relpkg in relpkgs:
                if subset.get(relpkg) is INSTALL:
                    if relpkg in locked:
                        raise Error, _("Package '%s' is locked") % relpkg
                    self.exclude(subset, relpkg, locked)

    def include(self, subset, pkg, locked=None):
        set = self._changeset

        if locked is None:
            locked = self._locked
            if self.DEBUG: print "-"*79
        else:
            locked = locked.copy()
        if self.DEBUG:
            strop = set.get(pkg) is INSTALL and "INSTALL" or "REMOVE"
            print "Including %s of %s" % (strop, pkg)

        if pkg not in set:
            raise Error, _("Package '%s' is not in changeset") % pkg
        if pkg in locked:
            raise Error, _("Package '%s' is locked") % pkg

        locked[pkg] = True

        op = subset[pkg] = set[pkg]
        try:
            if op is INSTALL:
                self._install(subset, pkg, locked)
            else:
                self._remove(subset, pkg, locked)
        except Error, e:
            if self.DEBUG:
                print "FAILED: Including %s of %s: %s" % (strop, pkg, e)
            del subset[pkg]
            raise

    def exclude(self, subset, pkg, locked=None):
        set = self._changeset

        if locked is None:
            locked = self._locked
            if self.DEBUG: print "-"*79
        else:
            locked = locked.copy()
        if self.DEBUG:
            strop = set.get(pkg) is INSTALL and "INSTALL" or "REMOVE"
            print "Excluding %s of %s" % (strop, pkg)

        if pkg not in set:
            raise Error, _("Package '%s' is not in changeset") % pkg
        if pkg in locked:
            raise Error, _("Package '%s' is locked") % pkg

        locked[pkg] = True

        if pkg in subset:
            del subset[pkg]

        op = set[pkg]
        try:
            if op is INSTALL:
                self._remove(subset, pkg, locked)
            elif op is REMOVE:
                self._install(subset, pkg, locked)
        except Error, e:
            if self.DEBUG:
                print "FAILED: Excluding %s of %s: %s" % (strop, pkg, e)
            subset[pkg] = op
            raise

    def includeAll(self, subset):
        # Include everything that doesn't change locked packages
        set = self._changeset.get()
        for pkg in set.keys():
            try:
                self.include(subset, pkg)
            except Error:
                pass

    def excludeAll(self, subset):
        # Exclude everything that doesn't change locked packages
        set = self._changeset.get()
        for pkg in set.keys():
            try:
                self.exclude(subset, pkg)
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

def forwardRequires(pkg, map):
    for req in pkg.requires:
        if req not in map:
            map[req] = True
            for prv in req.providedby:
                if prv not in map:
                    map[prv] = True
                    for prvpkg in prv.packages:
                        if prvpkg not in map:
                            map[prvpkg] = True
                            forwardRequires(prvpkg, map)

def backwardRequires(pkg, map):
    for prv in pkg.provides:
        if prv not in map:
            map[prv] = True
            for req in prv.requiredby:
                if req not in map:
                    map[req] = True
                    for reqpkg in req.packages:
                        if reqpkg not in map:
                            map[reqpkg] = True
                            backwardRequires(reqpkg, map)

def forwardPkgRequires(pkg, map=None):
    if map is None:
        map = {}
    forwardRequires(pkg, map)
    for item in map.keys():
        if not isinstance(item, Package):
            del map[item]
    return map

def backwardPkgRequires(pkg, map=None):
    if map is None:
        map = {}
    backwardRequires(pkg, map)
    for item in map.keys():
        if not isinstance(item, Package):
            del map[item]
    return map

def getAlternates(pkg, cache):
    """
    For a given package, return every package that *might* get
    removed if the given package was installed. The alternate
    packages are every package that conflicts with any of the
    required packages, or require any package conflicting with
    any of the required packages.
    """
    conflicts = {}

    # Direct conflicts.
    for namepkg in cache.getPackages(pkg.name):
        if namepkg is not pkg and not pkg.coexists(namepkg):
            conflicts[(pkg, namepkg)] = True
    for cnf in pkg.conflicts:
        for prv in cnf.providedby:
            for prvpkg in prv.packages:
                if prvpkg is not pkg:
                    conflicts[(pkg, prvpkg)] = True
    for prv in pkg.provides:
        for cnf in prv.conflictedby:
            for cnfpkg in cnf.packages:
                if cnfpkg is not pkg:
                    conflicts[(pkg, cnfpkg)] = True

    # Conflicts of requires.
    queue = [pkg]
    done = {}
    while queue:
        qpkg = queue.pop()
        done[qpkg] = True
        for req in qpkg.requires:
            prvpkgs = {}
            for prv in req.providedby:
                for prvpkg in prv.packages:
                    if prvpkg is qpkg or prvpkg is pkg:
                        break
                    prvpkgs[prvpkg] = True
                else:
                    continue
                break
            else:
                for prvpkg in prvpkgs:
                    if prvpkg in done:
                        continue
                    done[prvpkg] = True
                    queue.append(prvpkg)
                    for namepkg in cache.getPackages(prvpkg.name):
                        if (namepkg not in prvpkgs and
                            namepkg is not pkg and
                            not prvpkg.coexists(namepkg)):
                            conflicts[(prvpkg, namepkg)] = True
                    for cnf in prvpkg.conflicts:
                        for prv in cnf.providedby:
                            for _prvpkg in prv.packages:
                                if (_prvpkg is not pkg and
                                    _prvpkg not in prvpkgs):
                                    conflicts[(prvpkg, _prvpkg)] = True
                    for prv in prvpkg.provides:
                        for cnf in prv.conflictedby:
                            for cnfpkg in cnf.packages:
                                if (cnfpkg is not pkg and
                                    cnfpkg not in prvpkgs):
                                    conflicts[(prvpkg, cnfpkg)] = True

    alternates = {}
    for reqpkg, cnfpkg in conflicts:
        print reqpkg, cnfpkg
        alternates[cnfpkg] = True
        for prv in cnfpkg.provides:
            for req in prv.requiredby:
                # Do not ascend if reqpkg also provides
                # what cnfpkg is offering.
                for _prv in req.providedby:
                    if reqpkg in _prv.packages:
                        break
                else:
                    for _reqpkg in req.packages:
                        alternates[_reqpkg] = True
                        alternates.update(backwardPkgRequires(_reqpkg))

    return alternates

def checkPackagesSimple(cache, checkset=None, report=False,
                        installed=False, available=False):
    if installed and available:
        relateset = cache.getPackages()
    elif installed:
        relateset = [pkg for pkg in cache.getPackages() if pkg.installed]
    elif available:
        relateset = []
        for pkg in cache.getPackages():
            if not pkg.installed:
                relateset.append(pkg)
            else:
                for loader in pkg.loaders:
                    if not loader.getInstalled():
                        relateset.append(pkg)
                        break
    else:
        raise Error, "checkPackagesSimple() called with invalid parameters"
    if checkset is None:
        checkset = relateset
    return checkPackages(cache, checkset, relateset, report)

def checkPackages(cache, checkset, relateset, report=False):
    checkset = list(checkset)
    checkset.sort()
    relateset = dict.fromkeys(relateset, True)

    problems = False
    coexistchecked = {}
    for pkg in checkset:
        for req in pkg.requires:
            for prv in req.providedby:
                for prvpkg in prv.packages:
                    if prvpkg in relateset:
                        break
                else:
                    continue
                break
            else:
                if not report:
                    return False
                problems = True
                iface.info(_("Unsatisfied dependency: %s requires %s") %
                           (pkg, req))

        if not pkg.installed:
            continue

        for cnf in pkg.conflicts:
            for prv in cnf.providedby:
                for prvpkg in prv.packages:
                    if (prvpkg is not pkg and
                        prvpkg.installed and
                        prvpkg in relateset):
                        if not report:
                            return False
                        problems = True
                        iface.info(_("Unsatisfied dependency: "
                                     "%s conflicts with %s") % (pkg, prvpkg))

        namepkgs = cache.getPackages(pkg.name)
        for namepkg in namepkgs:
            if (namepkg is not pkg and
                namepkg.installed and
                namepkg in relateset and
                (namepkg, pkg) not in coexistchecked):
                coexistchecked[(pkg, namepkg)] = True
                if not pkg.coexists(namepkg):
                    if not report:
                        return False
                    problems = True
                    iface.info(_("Package %s can't coexist with %s") %
                               (namepkg, pkg))

    return not problems

def enablePsyco(psyco):
    psyco.bind(PolicyInstall.getWeight)
    psyco.bind(PolicyRemove.getWeight)
    psyco.bind(PolicyUpgrade.getWeight)
    psyco.bind(Transaction.getNecessary)
    psyco.bind(Transaction.getNecessitates)
    psyco.bind(Transaction.getProhibits)
    psyco.bind(Transaction.Task)
    psyco.bind(Transaction.TaskInstall)
    psyco.bind(Transaction.TaskRemove)
    psyco.bind(Transaction.TaskUpdown)
    psyco.bind(Transaction.TaskPending)
    psyco.bind(Transaction.TaskUpgrade)
    psyco.bind(Transaction.enqueue)
    psyco.bind(sortUpgrades)
    psyco.bind(recursiveUpgrades)
    psyco.bind(checkPackages)

hooks.register("enable-psyco", enablePsyco)

# vim:ts=4:sw=4:et

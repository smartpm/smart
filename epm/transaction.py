from epm import *

class LockedError(Exception): pass

class Transaction:
    def __init__(self, cache):
        self._cache = cache
        self._install = {}
        self._remove = {}
        self._locked = {}

    def getState(self):
        trans = Transaction(self._cache)
        trans._install = self._install.copy()
        trans._remove = self._remove.copy()
        trans._locked = self._locked.copy()

    def setState(self, state):
        self._install = state._install.copy()
        self._remove = state._remove.copy()
        self._locked = state._locked.copy()

    def setLocked(self, pkg, flag):
        if flag:
            self._locked[pkg] = True
        else:
            try:
                del self._locked[pkg]
            except KeyError:
                pass

    def getLocked(self, pkg):
        return self._locked.get(pkg, False)

    def setInstall(self, pkg):
        if not pkg.installed:
            logger.debug("installing "+str(pkg))
            self._install[pkg] = True
        else:
            logger.debug("keeping "+str(pkg))
            try:
                del self._remove[pkg]
            except KeyError:
                pass

    def setRemove(self, pkg):
        if pkg.installed:
            logger.debug("removing "+str(pkg))
            self._remove[pkg] = True
        else:
            logger.debug("keeping "+str(pkg))
            try:
                del self._install[pkg]
            except KeyError:
                pass

    def setKeep(self, pkg):
        logger.debug("keeping "+str(pkg))
        try:
            del self._install[pkg]
        except KeyError:
            pass
        try:
            del self._remove[pkg]
        except KeyError:
            pass

    def getInstall(self, pkg):
        return pkg in self._install

    def getRemove(self, pkg):
        return pkg in self._install

    def getKeep(self, pkg):
        return pkg not in self._install and pkg not in self._remove

    def getInstalled(self, pkg):
        return (pkg in self._install or
                pkg.installed and not pkg in self._remove)

    def __str__(self):
        lst = []
        lst.append(repr(self))
        for pkg in self._install:
            lst.append("  Install "+str(pkg))
        for pkg in self._remove:
            lst.append("  Remove  "+str(pkg))
        return "\n".join(lst)

class Operator:
    def __init__(self, trans):
        self._trans = trans
        self._cache = trans._cache

    def run(self, pkg=None):
        pass

    def getBrokenRequires(self, pkg=None):
        trans = self._trans
        broken = []
        if pkg:
            requires = pkg.requires
        else:
            requires = {}
            for pkg in self._cache.getPackages():
                if trans.getInstalled(pkg):
                    requires.update(dict.fromkeys(pkg.requires))
        for req in requires:
            for prv in req.providedby:
                for pkg in prv.packages:
                    if trans.getInstalled(pkg):
                        break
                else:
                    continue
                break
            else:
                broken.append(req)
        return broken

    def getBrokenObsoletes(self, pkg=None):
        trans = self._trans
        broken = []
        if pkg:
            provides = pkg.requires
        else:
            provides = {}
            for pkg in self._cache.getPackages():
                if trans.getInstalled(pkg):
                    provides.update(dict.fromkeys(pkg.provides))
        for prv in provides:
            for obs in prv.obsoletedby:
                for pkg in obs.packages:
                    if trans.getInstalled(pkg):
                        break
                else:
                    continue
                break
            else:
                broken.append(obs)
        return broken

    def getBrokenConflicts(self, pkg=None):
        trans = self._trans
        broken = []
        if pkg:
            provides = pkg.requires
        else:
            provides = {}
            for pkg in self._cache.getPackages():
                if trans.getInstalled(pkg):
                    provides.update(dict.fromkeys(pkg.provides))
        for prv in provides:
            for cnf in prv.conflictedby:
                for pkg in cnf.packages:
                    if trans.getInstalled(pkg):
                        break
                else:
                    continue
                break
            else:
                broken.append(cnf)
        return broken

class Solver(Operator):

    def run(self, pkg=None):
        logger.debug("starting problem solver")
        trans = self._trans
        cache = self._cache
        if pkg:
            packages = [pkg]
            for req in pkg.requires:
                provides.update(dict.fromkeys(req.providedby))
        else:
            packages = []
            for pkg in cache.getPackages():
                if trans.getInstalled(pkg):
                    packages.append(pkg)
        self._step_unsolvable(packages)
        self._step_upgrade(packages)
        logger.debug("finishing problem solver")

    def _step_unsolvable(self, packages):
        logger.debug("detecting unsolvable dependencies")
        trans = self._trans
        cache = self._cache
        found = False
        for pkg in packages:
            for req in self.getBrokenRequires(pkg):
                if not req.providedby:
                    found = True
                    logmsg = "%s has unsolvable requires: %s" % (pkg, req)
                    logger.debug(logmsg)
                    try:
                        lst = [pkg]
                        for pkg in lst:
                            trans.setRemove(pkg)
                            lst.extend([pkg for prv in pkg.provides
                                            for req in prv.requiredby
                                            for pkg in req.packages
                                            if trans.getInstalled(pkg)])
                    except LockedError:
                        raise Error, logmsg
                    break
        if not found:
            logger.debug("no unsolvable dependencies")

    def _step_upgrade(self, packages):
        logger.debug("trying to upgrade packages to solve problems")
        trans = self._trans
        cache = self._cache
        found = False
        for req in self.getBrokenRequires():
            for prv in req.providedby:
                for pkg in prv.packges:
                    candidates = cache.getPackages(pkg.name)

                    

# vim:ts=4:sw=4:et


class Package(object):
    def __init__(self, name, version):
        self.name = name
        self.version = version
        self.provides = []
        self.requires = []
        self.upgrades = []
        self.conflicts = []
        self.installed = False
        self.essential = False
        self.precedence = 0
        self.loaderinfo = {}

    def equals(self, other):
        # These two packages are exactly the same?
        fk = dict.fromkeys
        if (self.name != other.name or
            self.version != other.version or
            len(self.provides) != len(other.provides) or
            len(self.requires) != len(other.requires) or
            len(self.upgrades) != len(other.upgrades) or
            len(self.conflicts) != len(other.conflicts) or
            fk(self.provides) != fk(other.provides) or
            fk(self.requires) != fk(other.requires) or
            fk(self.upgrades) != fk(other.upgrades) or
            fk(self.conflicts) != fk(other.conflicts)):
            return False
        return True

    def coexists(self, other):
        # These two packages with the same name may coexist?
        # Use this for cases where two different packages have the
        # same name-version. In these cases, mapping the issue to a
        # conflicts/upgrades relation is impossible, since the relation
        # would match the package itself. *DO NOT* use this as a
        # shortcut for other kinds of conflicts/upgrades. The
        # transaction system handles these cases differently.
        return self.version != other.version

    def matches(self, relation, version):
        return False

    def __str__(self):
        return "%s-%s" % (self.name, self.version)

    def __cmp__(self, other):
        # Basic comparison. Should be overloaded.
        rc = -1
        if isinstance(other, Package):
            rc = cmp(self.name, other.name)
            if rc == 0:
                rc = cmp(self.version, other.version)
        return rc

class PackageInfo(object):
    def __init__(self, package):
        self._package = package

    def getPackage(self):
        return self._package

    def getURL(self):
        return None

    def getDescription(self):
        return ""

    def getSummary(self):
        return ""

    def getPathList(self):
        return []

    def pathIsDir(self, path):
        return None

    def pathIsLink(self, path):
        return None

    def pathIsFile(self, path):
        return None

    def pathIsSpecial(self, path):
        return None

    def getSize(self):
        return 0

    def getInstalledSize(self):
        return 0

    def getMD5(self):
        return None

    def getSHA(self):
        return None

class Provides(object):
    def __init__(self, name, version=None):
        self.name = name
        self.version = version
        self.packages = []
        self.requiredby = []
        self.upgradedby = []
        self.conflictedby = []

    def __str__(self):
        if self.version:
            return "%s = %s" % (self.name, self.version)
        return self.name

    def __cmp__(self, other):
        rc = cmp(self.name, other.name)
        if rc == 0:
            rc = cmp(self.version, other.version)
        return rc

class Depends(object):
    def __init__(self, name, relation=None, version=None):
        self.name = name
        self.relation = relation
        self.version = version
        self.packages = []
        self.providedby = []

    def matches(self, prv):
        return False

    def __str__(self):
        if self.version:
            return "%s %s %s" % (self.name, self.relation, self.version)
        else:
            return self.name

    def __cmp__(self, other):
        rc = cmp(self.name, other.name)
        if rc == 0:
            rc = cmp(self.version, other.version)
        return rc

class PreRequires(Depends): pass
class Requires(Depends): pass
class Upgrades(Depends): pass
class Conflicts(Depends): pass

class Loader(object):
    def __init__(self):
        self._repository = None
        self._cache = None
        self._installed = False
        self.reset()

    def getRepository(self):
        return self._repository

    def setRepository(self, repository):
        self._repository = repository

    def getCache(self):
        return self._cache

    def setCache(self, cache):
        self._cache = cache

    def getInstalled(self):
        return self._installed

    def setInstalled(self, flag):
        self._installed = flag

    def getLoadSteps(self):
        return 0

    def getInfo(self, pkg):
        return None

    def reset(self):
        self._packages = []

    def load(self):
        pass

    def unload(self):
        self.reset()

    def loadFileProvides(self, fndict):
        pass

    def reload(self):
        cache = self._cache
        cache._packages.extend(self._packages)
        for pkg in self._packages:
            lst = cache._pkgnames.get(pkg.name)
            if lst is not None:
                lst.append(pkg)
            else:
                cache._pkgnames[pkg.name] = [pkg]
            for prv in pkg.provides:
                prv.packages.append(pkg)
                args = (prv.name, prv.version)
                if not cache._prvmap.get(args):
                    cache._provides.append(prv)
                    cache._prvmap[args] = prv
                    lst = cache._prvnames.get(prv.name)
                    if lst is not None:
                        lst.append(prv)
                    else:
                        cache._prvnames[prv.name] = [prv]
            for req in pkg.requires:
                req.packages.append(pkg)
                args = (req.name, req.version, req.relation)
                if not cache._reqmap.get(args):
                    cache._requires.append(req)
                    cache._reqmap[args] = req
                    lst = cache._reqnames.get(req.name)
                    if lst is not None:
                        lst.append(req)
                    else:
                        cache._reqnames[req.name] = [req]
            for upg in pkg.upgrades:
                upg.packages.append(upg)
                args = (upg.name, upg.version, upg.relation)
                if not cache._upgmap.get(args):
                    cache._upgrades.append(upg)
                    cache._upgmap[args] = upg
                    lst = cache._upgnames.get(upg.name)
                    if lst is not None:
                        lst.append(upg)
                    else:
                        cache._upgnames[upg.name] = [upg]
            for cnf in pkg.conflicts:
                cnf.packages.append(pkg)
                args = (cnf.name, cnf.version, cnf.relation)
                if not cache._upgmap.get(args):
                    cache._conflicts.append(cnf)
                    cache._upgmap[args] = cnf
                    lst = cache._cnfnames.get(cnf.name)
                    if lst is not None:
                        lst.append(cnf)
                    else:
                        cache._cnfnames[cnf.name] = [cnf]

    def newPackage(self, pkgargs, prvargs, reqargs, upgargs, cnfargs):
        cache = self._cache
        pkg = pkgargs[0](*pkgargs[1:])
        relpkgs = []
        if prvargs:
            for args in prvargs:
                prv = cache._prvmap.get(args)
                if not prv:
                    prv = args[0](*args[1:])
                    cache._prvmap[args] = prv
                    lst = cache._prvnames.get(prv.name)
                    if lst is not None:
                        lst.append(prv)
                    else:
                        cache._prvnames[prv.name] = [prv]
                    cache._provides.append(prv)
                relpkgs.append(prv.packages)
                pkg.provides.append(prv)

        if reqargs:
            for args in reqargs:
                req = cache._reqmap.get(args)
                if not req:
                    req = args[0](*args[1:])
                    cache._reqmap[args] = req
                    lst = cache._reqnames.get(req.name)
                    if lst is not None:
                        lst.append(req)
                    else:
                        cache._reqnames[req.name] = [req]
                    cache._requires.append(req)
                relpkgs.append(req.packages)
                pkg.requires.append(req)

        if upgargs:
            for args in upgargs:
                upg = cache._upgmap.get(args)
                if not upg:
                    upg = args[0](*args[1:])
                    cache._upgmap[args] = upg
                    lst = cache._upgnames.get(upg.name)
                    if lst is not None:
                        lst.append(upg)
                    else:
                        cache._upgnames[upg.name] = [upg]
                    cache._upgrades.append(upg)
                relpkgs.append(upg.packages)
                pkg.upgrades.append(upg)

        if cnfargs:
            for args in cnfargs:
                cnf = cache._upgmap.get(args)
                if not cnf:
                    cnf = args[0](*args[1:])
                    cache._upgmap[args] = cnf
                    lst = cache._cnfnames.get(cnf.name)
                    if lst is not None:
                        lst.append(cnf)
                    else:
                        cache._cnfnames[cnf.name] = [cnf]
                    cache._conflicts.append(cnf)
                relpkgs.append(cnf.packages)
                pkg.conflicts.append(cnf)

        found = False
        lst = cache._pkgmap.get(pkgargs)
        if lst is not None:
            for lstpkg in lst:
                if pkg.equals(lstpkg):
                    pkg = lstpkg
                    found = True
                    break
            else:
                lst.append(pkg)
        else:
            cache._pkgmap[pkgargs] = [pkg]

        if not found:
            cache._packages.append(pkg)
            lst = cache._pkgnames.get(pkg.name)
            if lst is not None:
                lst.append(pkg)
            else:
                cache._pkgnames[pkg.name] = [pkg]
            for pkgs in relpkgs:
                pkgs.append(pkg)

        pkg.installed |= self._installed
        self._packages.append(pkg)

        return pkg

    def newProvides(self, pkg, prvargs):
        cache = self._cache
        prv = cache._prvmap.get(prvargs)
        if not prv:
            prv = prvargs[0](*prvargs[1:])
            cache._prvmap[prvargs] = prv
            lst = cache._prvnames.get(prv.name)
            if lst is not None:
                lst.append(prv)
            else:
                cache._prvnames[prv.name] = [prv]
            cache._provides.append(prv)
        prv.packages.append(pkg)
        pkg.provides.append(prv)

        if prv.name[0] == "/":
            for req in pkg.requires[:]:
                if req.name == prv.name:
                    pkg.requires.remove(req)
                    req.packages.remove(pkg)
                    if not req.packages:
                        cache._requires.remove(req)
                        lst = cache._reqnames[req.name]
                        if len(lst) == 1:
                            del cache._reqnames[req.name]
                        else:
                            lst.remove(req)
                        reqargs = (req.__class__,
                                   req.name, req.relation, req.version)
                        del cache._reqmap[reqargs]

    def newRequires(self, pkg, reqargs):
        cache = self._cache
        req = cache._reqmap.get(reqargs)
        if not req:
            req = reqargs[0](*reqargs[1:])
            cache._reqmap[reqargs] = req
            lst = cache._reqnames.get(req.name)
            if lst is not None:
                lst.append(req)
            else:
                cache._reqnames[req.name] = [req]
            cache._requires.append(req)
        req.packages.append(pkg)
        pkg.requires.append(req)

    def newUpgrades(self, pkg, upgargs):
        cache = self._cache
        upg = cache._upgmap.get(upgargs)
        if not upg:
            upg = upgargs[0](*upgargs[1:])
            cache._upgmap[upgargs] = upg
            lst = cache._upgnames.get(upg.name)
            if lst is not None:
                lst.append(upg)
            else:
                cache._upgnames[upg.name] = [upg]
            cache._upgrades.append(upg)
        upg.packages.append(pkg)
        pkg.upgrades.append(upg)

    def newConflicts(self, pkg, cnfargs):
        cache = self._cache
        cnf = cache._cnfmap.get(cnfargs)
        if not cnf:
            cnf = cnfargs[0](*cnfargs[1:])
            cache._cnfmap[cnfargs] = cnf
            lst = cache._cnfnames.get(cnf.name)
            if lst is not None:
                lst.append(cnf)
            else:
                cache._cnfnames[cnf.name] = [cnf]
            cache._conflicts.append(cnf)
        cnf.packages.append(pkg)
        pkg.conflicts.append(cnf)

class LoaderSet(list):

    def getRepository(self):
        if self:
            return self[0].getRepository()
        return None

    def setRepository(self, repository):
        for loader in self:
            loader.setRepository(repository)

    def getCache(self):
        if self:
            return self[0].getCache()
        return None

    def setCache(self, cache):
        for loader in self:
            loader.setCache(cache)

    def getLoadSteps(self):
        steps = 0
        for loader in self:
            steps += loader.getLoadSteps()
        return steps

    def reset(self):
        for loader in self:
            loader.reset()

    def load(self):
        for loader in self:
            loader.load()

    def loadFileProvides(self, fndict):
        for loader in self:
            loader.loadFileProvides(fndict)

    def unload(self):
        for loader in self:
            loader.unload()

    def reload(self):
        for loader in self:
            loader.reload()

class Cache(object):
    def __init__(self):
        self._loaders = []
        self._packages = []
        self._provides = []
        self._requires = []
        self._upgrades = []
        self._conflicts = []
        self._pkgnames = {}
        self._prvnames = {}
        self._reqnames = {}
        self._upgnames = {}
        self._cnfnames = {}
        self._pkgmap = {}
        self._prvmap = {}
        self._reqmap = {}
        self._upgmap = {}
        self._cnfmap = {}

    def reset(self, deps=False):
        # Do not lose references to current objects, since
        # loader may want to cache them internally.
        if deps:
            for prv in self._provides:
                del prv.packages[:]
                del prv.requiredby[:]
                del prv.upgradedby[:]
                del prv.conflictedby[:]
            for req in self._requires:
                del req.packages[:]
                del req.providedby[:]
            for upg in self._upgrades:
                del upg.packages[:]
                del upg.providedby[:]
            for cnf in self._conflicts:
                del cnf.packages[:]
                del cnf.providedby[:]
        del self._packages[:]
        del self._provides[:]
        del self._requires[:]
        del self._upgrades[:]
        del self._conflicts[:]
        self._pkgnames.clear()
        self._prvnames.clear()
        self._reqnames.clear()
        self._upgnames.clear()
        self._cnfnames.clear()
        self._prvmap.clear()
        self._reqmap.clear()
        self._upgmap.clear()
        self._cnfmap.clear()

    def addLoader(self, loader):
        if loader:
            self._loaders.append(loader)
            loader.setCache(self)

    def removeLoader(self, loader):
        if loader:
            self._loaders.remove(loader)
            loader.setCache(None)

    def load(self):
        self.reset()
        prog = iface.getProgress(self)
        prog.start()
        prog.setTopic("Building cache...")
        prog.set(0, 1)
        prog.show()
        total = 1
        for loader in self._loaders:
            total += loader.getLoadSteps()
        prog.set(0, total)
        prog.show()
        for loader in self._loaders:
            loader.reset()
            loader.load()
        self.loadFileProvides()
        self.linkDeps()
        prog.add(1)
        prog.show()
        prog.stop()

    def unload(self):
        self.reset()
        for loader in self._loaders:
            loader.unload()

    def reload(self):
        self.reset(True)
        for loader in self._loaders:
            loader.reload()
        self.loadFileProvides()
        self.linkDeps()

    def loadFileProvides(self):
        fndict = {}
        for req in self._requires:
            if req.name[0] == "/":
                fndict[req.name] = True
        for loader in self._loaders:
            loader.loadFileProvides(fndict)

    def linkDeps(self):
        for prv in self._provides:
            lst = self._reqnames.get(prv.name)
            if lst:
                for req in lst:
                    if req.matches(prv):
                        req.providedby.append(prv)
                        prv.requiredby.append(req)
            lst = self._upgnames.get(prv.name)
            if lst:
                for upg in lst:
                    if upg.matches(prv):
                        upg.providedby.append(prv)
                        prv.upgradedby.append(upg)
            lst = self._cnfnames.get(prv.name)
            if lst:
                for cnf in lst:
                    if cnf.matches(prv):
                        cnf.providedby.append(prv)
                        prv.conflictedby.append(cnf)

    def getPackages(self, name=None):
        if not name:
            return self._packages
        else:
            return self._pkgnames.get(name, [])

    def getProvides(self, name=None):
        if not name:
            return self._provides
        else:
            return self._prvnames.get(name, [])

    def getRequires(self, name=None):
        if not name:
            return self._requires
        else:
            return self._reqnames.get(name, [])

    def getUpgrades(self, name=None):
        if not name:
            return self._upgrades
        else:
            return self._upgnames.get(name, [])

    def getConflicts(self, name=None):
        if not name:
            return self._conflicts
        else:
            return self._cnfnames.get(name, [])

from ccache import *

# vim:ts=4:sw=4:et

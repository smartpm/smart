#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Gepeto.
#
# Gepeto is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gepeto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gepeto; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from gepeto.const import BLOCKSIZE
from gepeto import *
import os

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
        self.priority = 0
        self.loaders = {}

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
        return False

    def matches(self, relation, version):
        return False

    def getPriority(self):
        priority = sysconf.getPriority(self)
        if priority is not None:
            return priority
        channelpriority = None
        for loader in self.loaders:
            priority = loader.getChannel().getPriority()
            if channelpriority is None or priority > channelpriority:
                channelpriority = priority
        return channelpriority+self.priority

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

    def getURLs(self):
        return []

    def getDescription(self):
        return ""

    def getSummary(self):
        return ""

    def getGroup(self):
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

    def validate(self, localpath, withreason=False):
        try:
            if not os.path.isfile(localpath):
                raise Error, "File not found"

            size = self.getSize()
            if size:
                lsize = os.path.getsize(localpath)
                if lsize != size:
                    raise Error, "Unexpected size (expected %d, got %d)" % \
                                 (size, lsize)

            filemd5 = self.getMD5()
            if filemd5:
                import md5
                digest = md5.md5()
                file = open(localpath)
                data = file.read(BLOCKSIZE)
                while data:
                    digest.update(data)
                    data = file.read(BLOCKSIZE)
                lfilemd5 = digest.hexdigest()
                if lfilemd5 != filemd5:
                    raise Error, "Invalid MD5 (expected %s, got %s)" % \
                                 (filemd5, lfilemd5)
            else:
                filesha = self.getSHA()
                if filesha:
                    import sha
                    digest = sha.sha()
                    file = open(localpath)
                    data = file.read(BLOCKSIZE)
                    while data:
                        digest.update(data)
                        data = file.read(BLOCKSIZE)
                    lfilesha = digest.hexdigest()
                    if lfilesha != filesha:
                        raise Error, "Invalid SHA (expected %s, got %s)" % \
                                     (filesha, lfilesha)
        except Error, reason:
            if withreason:
                return False, reason
            return False
        else:
            if withreason:
                return True, None
            return True

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
            if rc == 0:
                rc = cmp(self.__class__, other.__class__)
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
            if rc == 0:
                rc = cmp(self.__class__, other.__class__)
        return rc

class PreRequires(Depends): pass
class Requires(Depends): pass
class Upgrades(Depends): pass
class Conflicts(Depends): pass

class Loader(object):
    def __init__(self):
        self._packages = []
        self._channel = None
        self._cache = None
        self._installed = False

    def getPackages(self):
        return self._packages

    def getChannel(self):
        return self._channel

    def setChannel(self, channel):
        self._channel = channel

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
        del self._packages[:]

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

        if prv in pkg.provides:
            return

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
        if req in pkg.requires:
            return
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
        if upg in pkg.upgrades:
            return
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
        if cnf in pkg.conflicts:
            return
        cnf.packages.append(pkg)
        pkg.conflicts.append(cnf)

class LoaderSet(list):

    def getPackages(self):
        packages = []
        for loader in self:
            packages.extend(loader.getPackages())
        return packages

    def getChannel(self):
        if self:
            return self[0].getChannel()
        return None

    def setChannel(self, channel):
        for loader in self:
            loader.setChannel(channel)

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

from cpm.transaction import ChangeSet, ChangeSetSplitter, INSTALL, REMOVE
from cpm.repository import createRepository
from cpm.fetcher import Fetcher
from cpm.cache import Cache
from cpm.const import *
from cpm import *
import os, md5

class Control:

    def __init__(self):
        self._conffile = CONFFILE
        self._confdigest = None
        self._replst = []
        self._sysconfreplst = []
        self._cache = Cache()
        self._fetcher = Fetcher()

    def getRepositories(self):
        return self._replst

    def addRepository(self, repos):
        self._replst.append(repos)

    def removeRepository(self, repos):
        if repos in self._sysconfreplst:
            raise Error, "Repository is in system configuration"
        self._replst.remove(repos)

    def getCache(self):
        return self._cache

    def getFetcher(self):
        return self._fetcher

    def loadCache(self):
        self._cache.load()

    def reloadCache(self):
        self._cache.reload()

    def loadSysConf(self, conffile=None):
        loaded = False
        if conffile:
            conffile = os.path.expanduser(conffile)
            if not os.path.isfile(conffile):
                raise Error, "Configuration file not found: %s" % conffile
            sysconf.load(conffile)
            loaded = True
        else:
            conffile = os.path.expanduser(CONFFILE)
            if os.path.isfile(conffile):
                sysconf.load(conffile)
                loaded = True
        self._conffile = conffile
        if loaded:
            self._confdigest = md5.md5(str(sysconf.getMap())).digest()
        else:
            self._confdigest = None

    def saveSysConf(self, conffile=None):
        if not conffile:
            confdigest = md5.md5(str(sysconf.getMap())).digest()
            if confdigest == self._confdigest:
                return
            self._confdigest = confdigest
            conffile = self._conffile
        conffile = os.path.expanduser(conffile)
        sysconf.save(conffile)

    def reloadSysConfRepositories(self):
        for repos in self._sysconfreplst:
            self._replst.remove(repos)
            self._cache.removeLoader(repos.getLoader())
        self._replst = [x for x in self._replst
                              if x not in self._sysconfreplst]
        names = {}
        for data in sysconf.get("repositories", ()):
            if data.get("disabled"):
                continue
            type = data.get("type")
            if not type:
                raise Error, "Repository without type in configuration"
            repos = createRepository(type, data)
            name = repos.getName()
            if names.get(name):
                raise Error, "'%s' is not a unique repository name" % name
            else:
                names[name] = True
            self._sysconfreplst.append(repos)
            self._replst.append(repos)

    def fetchRepositories(self, replst=None, caching=ALWAYS):
        if replst is None:
            self.reloadSysConfRepositories()
            replst = self._replst
        localdir = os.path.join(sysconf.get("data-dir"), "repositories/")
        if not os.path.isdir(localdir):
            os.makedirs(localdir)
        self._fetcher.setLocalDir(localdir, mangle=True)
        self._fetcher.setCaching(caching)
        for repos in replst:
            self._cache.removeLoader(repos.getLoader())
            repos.fetch(self._fetcher)
            self._cache.addLoader(repos.getLoader())

    def fetchPackages(self, packages, caching=OPTIONAL):
        fetcher = self._fetcher
        fetcher.reset()
        fetcher.setCaching(caching)
        localdir = os.path.join(sysconf.get("data-dir"), "packages/")
        if not os.path.isdir(localdir):
            os.makedirs(localdir)
        self._fetcher.setLocalDir(localdir, mangle=False)
        pkgurl = {}
        for pkg in packages:
            loader = [x for x in pkg.loaders if not x.getInstalled()][0]
            info = loader.getInfo(pkg)
            url = info.getURL()
            pkgurl[pkg] = url
            fetcher.enqueue(url)
            fetcher.setInfo(url, size=info.getSize(), md5=info.getMD5(),
                            sha=info.getSHA())
        fetcher.run("packages")
        failed = fetcher.getFailedSet()
        if failed:
            raise Error, "Failed to download packages:\n" + \
                         "\n".join(["    %s: %s" % (url, failed[url])
                                    for url in failed])
        succeeded = self._fetcher.getSucceededSet()
        pkgpath = {}
        for pkg in packages:
            pkgpath[pkg] = succeeded[pkgurl[pkg]]
        return pkgpath

    def fetchFiles(self, urllst, what, caching=NEVER):
        localdir = os.path.join(sysconf.get("data-dir"), "tmp/")
        if not os.path.isdir(localdir):
            os.makedirs(localdir)
        fetcher = self._fetcher
        fetcher.setLocalDir(localdir, mangle=True)
        fetcher.setCaching(caching)
        for url in urllst:
            fetcher.enqueue(url)
        fetcher.run(what)
        return fetcher.getSucceededSet(), fetcher.getFailedSet()

    def commitTransaction(self, trans, caching=OPTIONAL, confirm=True):
        if not confirm or iface.confirmTransaction(trans):
            self.commitChangeSet(trans.getChangeSet(), caching)

    def commitChangeSet(self, changeset, caching=OPTIONAL):
        pkgpath = self.fetchPackages([pkg for pkg in changeset
                                      if changeset[pkg] is INSTALL],
                                      caching)
        pmpkgs = {}
        for pkg in changeset:
            pmclass = pkg.packagemanager
            if pmclass not in pmpkgs:
                pmpkgs[pmclass] = [pkg]
            else:
                pmpkgs[pmclass].append(pkg)
        for pmclass in pmpkgs:
            pm = pmclass()
            pminstall = [pkg for pkg in pmpkgs[pmclass]
                         if changeset[pkg] is INSTALL]
            pmremove  = [pkg for pkg in pmpkgs[pmclass]
                         if changeset[pkg] is REMOVE]
            pm.commit(pminstall, pmremove, pkgpath)

    def commitTransactionStepped(self, trans, caching=OPTIONAL, confirm=True):
        if not confirm or iface.confirmTransaction(trans):
            self.commitChangeSetStepped(trans.getChangeSet(), caching)

    def commitChangeSetStepped(self, changeset, caching=OPTIONAL):

        # Order by number of required packages inside the transaction.
        pkglst = []
        for pkg in changeset:
            n = 0
            for req in pkg.requires:
                for prv in req.providedby:
                    for prvpkg in prv.packages:
                        if changeset.get(prvpkg) is INSTALL:
                            n += 1
            pkglst.append((n, pkg))

        pkglst.sort()

        splitter = ChangeSetSplitter(changeset)
        unioncs = ChangeSet(self._cache)
        for n, pkg in pkglst:
            if pkg in unioncs:
                continue
            cs = ChangeSet(self._cache, unioncs)
            splitter.include(unioncs, pkg)
            cs = unioncs.difference(cs)
            self.commitChangeSet(cs)

# vim:ts=4:sw=4:et

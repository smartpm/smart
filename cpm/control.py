from cpm.transaction import ChangeSet, ChangeSetSplitter, INSTALL, REMOVE
from cpm.fetcher import Fetcher
from cpm.cache import Cache
from cpm.const import *
from cpm import *

class Control:

    def __init__(self, feedback=None):
        self._repositories = sysconf.get("repositories", [])
        if not feedback:
            feedback = ControlFeedback()
        self._feedback = feedback
        self._cache = Cache()
        feedback.cacheCreated(self._cache)
        self._fetcher = Fetcher()
        feedback.fetcherCreated(self._fetcher)

    def setFeedback(self, feedback):
        self._feedback = feedback

    def getFeedback(self, feedback):
        return self._feedback

    def getRepositories(self):
        return self._repositories

    def setRepositories(self, repositories):
        self._repositories = repositories

    def getCache(self):
        return self._cache

    def getFetcher(self):
        return self._fetcher

    def loadCache(self):
        self._cache.load()

    def reloadCache(self):
        self._cache.reload()

    def fetchRepositories(self, repositories=None, caching=ALWAYS):
        if not repositories:
            repositories = self._repositories
        self._fetcher.setCaching(caching)
        self._feedback.fetcherStarting(self._fetcher)
        for repos in repositories:
            self._cache.removeLoader(repos.getLoader())
            repos.fetch(self._fetcher)
            self._cache.addLoader(repos.getLoader())
        self._feedback.fetcherFinished(self._fetcher)

    def fetchPackages(self, packages, caching=OPTIONAL):
        fetcher = self._fetcher
        fetcher.reset()
        fetcher.setCaching(caching)
        pkgurl = {}
        for pkg in packages:
            loader = [x for x in pkg.loaderinfo if not x.getInstalled()][0]
            info = loader.getInfo(pkg)
            url = info.getURL()
            pkgurl[pkg] = url
            fetcher.enqueue(url)
            fetcher.setInfo(url, size=info.getSize(), md5=info.getMD5(),
                            sha=info.getSHA())
        self._feedback.fetcherStarting(fetcher)
        fetcher.run("packages")
        self._feedback.fetcherFinished(fetcher)
        failed = fetcher.getFailedSet()
        if failed:
            raise Error, "failed to download packages:\n" + \
                         "\n".join(["    %s: %s" % (url, failed[url])
                                    for url in failed])
        succeeded = self._fetcher.getSucceededSet()
        pkgpath = {}
        for pkg in packages:
            pkgpath[pkg] = succeeded[pkgurl[pkg]]
        return pkgpath

    def commitTransaction(self, trans, caching=OPTIONAL):
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
            self._feedback.packageManagerCreated(pm)
            pminstall = [pkg for pkg in pmpkgs[pmclass]
                         if changeset[pkg] is INSTALL]
            pmremove  = [pkg for pkg in pmpkgs[pmclass]
                         if changeset[pkg] is REMOVE]
            self._feedback.packageManagerStarting(pm)
            pm.commit(pminstall, pmremove, pkgpath)
            self._feedback.packageManagerFinished(pm)

    def commitTransactionStepped(self, trans, caching=OPTIONAL):
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
        unioncs = ChangeSet()
        for n, pkg in pkglst:
            if pkg in unioncs:
                continue
            cs = ChangeSet(unioncs)
            splitter.include(unioncs, pkg)
            cs = unioncs.difference(cs)
            self.commitChangeSet(cs)

class ControlFeedback:

    def cacheCreated(self, cache):
        pass

    def fetcherCreated(self, fetcher):
        pass

    def fetcherStarting(self, fetcher):
        pass

    def fetcherFinished(self, fetcher):
        pass

    def packageManagerCreated(self, pm):
        pass

    def packageManagerStarting(self, pm):
        pass

    def packageManagerFinished(self, pm):
        pass

# vim:ts=4:sw=4:et

from cpm.transaction import ChangeSet, ChangeSetSplitter, INSTALL, REMOVE
from cpm.channel import createChannel
from cpm.progress import Progress
from cpm.fetcher import Fetcher
from cpm.cache import Cache
from cpm.const import *
from cpm import *
import os, md5

class Control:

    def __init__(self):
        self._conffile = CONFFILE
        self._confdigest = None
        self._channels = []
        self._sysconfchannels = []
        self._cache = Cache()
        self._fetcher = Fetcher()

    def getChannels(self):
        return self._channels

    def addChannel(self, channel):
        self._channels.append(channel)

    def removeChannel(self, channel):
        if channel in self._sysconfchannels:
            raise Error, "Channel is in system configuration"
        self._channels.remove(channel)

    def getCache(self):
        return self._cache

    def getFetcher(self):
        return self._fetcher

    def loadCache(self):
        self._cache.load()

    def unloadCache(self):
        self._cache.unload()

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

    def reloadSysConfChannels(self):
        for channel in self._sysconfchannels:
            self._channels.remove(channel)
            self._cache.removeLoader(channel.getLoader())
        del self._sysconfchannels[:]
        names = {}
        for data in sysconf.get("channels", ()):
            if data.get("disabled"):
                continue
            type = data.get("type")
            if not type:
                raise Error, "Channel without type in configuration"
            channel = createChannel(type, data)
            name = channel.getName()
            if names.get(name):
                raise Error, "'%s' is not a unique channel name" % name
            else:
                names[name] = True
            self._sysconfchannels.append(channel)
            self._channels.append(channel)

    def updateCache(self, fetchchannels=None, caching=ALWAYS):
        self._cache.unload()
        self.fetchChannels(fetchchannels, caching=caching)
        self._cache.load()

    def fetchChannels(self, channels=None, caching=ALWAYS):
        if channels is None:
            self.reloadSysConfChannels()
            channels = self._channels
        localdir = os.path.join(sysconf.get("data-dir"), "channels/")
        if not os.path.isdir(localdir):
            os.makedirs(localdir)
        self._fetcher.setLocalDir(localdir, mangle=True)
        self._fetcher.setCaching(caching)
        channels.sort()
        if caching is ALWAYS:
            progress = Progress()
        else:
            progress = iface.getProgress(self._fetcher, True)
        progress.start()
        steps = 0
        for channel in channels:
            steps += channel.getFetchSteps()
        progress.set(0, steps)
        for channel in channels:
            self._cache.removeLoader(channel.getLoader())
            if channel.getFetchSteps() > 0:
                progress.setTopic("Fetching information for '%s'..." %
                                  channel.getName())
                progress.show()
            channel.fetch(self._fetcher, progress)
            self._cache.addLoader(channel.getLoader())
        progress.setDone()
        progress.show()
        progress.stop()

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
            fetcher.enqueue(url, validate=info.validate)
        fetcher.run(what="packages")
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
        fetcher.run(what=what)
        return fetcher.getSucceededSet(), fetcher.getFailedSet()

    def commitTransaction(self, trans, caching=OPTIONAL, confirm=True):
        if not confirm or iface.confirmTransaction(trans):
            return self.commitChangeSet(trans.getChangeSet(), caching)
        return False

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

        return True

    def commitTransactionStepped(self, trans, caching=OPTIONAL, confirm=True):
        if not confirm or iface.confirmTransaction(trans):
            return self.commitChangeSetStepped(trans.getChangeSet(), caching)
        return False

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

        return True

# vim:ts=4:sw=4:et

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
from gepeto.transaction import ChangeSet, ChangeSetSplitter, INSTALL, REMOVE
from gepeto.channel import createChannel, FileChannel
from gepeto.util.strtools import strToBool
from gepeto.progress import Progress
from gepeto.fetcher import Fetcher
from gepeto.cache import Cache
from gepeto.const import *
from gepeto import *
import sys, os
import md5

class Control(object):

    def __init__(self, conffile=None):
        self._conffile = None
        self._confdigest = None
        self._channels = []
        self._sysconfchannels = []

        self.loadSysConf(conffile)

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

    def getFileChannels(self):
        return [x for x in self._channels if isinstance(x, FileChannel)]

    def addFileChannel(self, filename):
        if not self._sysconfchannels:
            # Give a chance for backends to register
            # themselves on FileChannel hooks.
            self.reloadSysConfChannels()
        self._channels.append(FileChannel(filename))

    def removeFileChannel(self, filename):
        for channel in self._channels:
            if (isinstance(channel, FileChannel) and
                channel.getAlias() == os.path.abspath(filename)):
                self._filechannels.remove(channel)
                break
        else:
            raise Error, "Channel not found for '%s'" % filename

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
        datadir = sysconf.get("data-dir")
        if conffile:
            conffile = os.path.expanduser(conffile)
            if not os.path.isfile(conffile):
                raise Error, "Configuration file not found: %s" % conffile
            sysconf.load(conffile)
            loaded = True
        else:
            conffile = os.path.join(datadir, CONFFILE)
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
        dirname = os.path.dirname(conffile)
        if not os.path.isdir(dirname) or os.access(dirname, os.W_OK):
            sysconf.save(conffile)

    def reloadSysConfChannels(self):
        for channel in self._sysconfchannels:
            self._channels.remove(channel)
            self._cache.removeLoader(channel.getLoader())
        del self._sysconfchannels[:]
        channels = sysconf.get("channels", ())
        for alias in channels:
            data = channels[alias]
            if strToBool(data.get("disabled")):
                continue
            type = data.get("type")
            if not type:
                raise Error, "Channel without type in configuration"
            channel = createChannel(type, alias, data)
            self._sysconfchannels.append(channel)
            self._channels.append(channel)

    def updateCache(self, channels=None, caching=ALWAYS):
        if channels is None:
            manual = False
            self.reloadSysConfChannels()
            channels = self._channels
        else:
            manual = True
        localdir = os.path.join(sysconf.get("data-dir"), "channels/")
        if not os.path.isdir(localdir):
            os.makedirs(localdir)
        self._fetcher.setLocalDir(localdir, mangle=True)
        channels.sort()
        if caching is ALWAYS:
            progress = Progress()
        else:
            progress = iface.getProgress(self._fetcher, True)
            oldpkgs = {}
            for pkg in self._cache.getPackages():
                oldpkgs[(pkg.name, pkg.version)] = True
        self._cache.unload()
        progress.start()
        steps = 0
        for channel in channels:
            steps += channel.getFetchSteps()
        progress.set(0, steps)
        for channel in channels:
            self._cache.removeLoader(channel.getLoader())
            if not manual and channel.getManualUpdate():
                self._fetcher.setCaching(ALWAYS)
            else:
                self._fetcher.setCaching(caching)
                if channel.getFetchSteps() > 0:
                    progress.setTopic("Fetching information for '%s'..." %
                                  (channel.getName() or channel.getAlias()))
                    progress.show()
            try:
                channel.fetch(self._fetcher, progress)
            except Error, e:
                iface.error(str(e))
            self._cache.addLoader(channel.getLoader())
        progress.setStopped()
        progress.show()
        progress.stop()
        self._cache.load()
        if caching is not ALWAYS:
            sysconf.clearFlag("new")
            for pkg in self._cache.getPackages():
                if (pkg.name, pkg.version) not in oldpkgs:
                    sysconf.setFlag("new", pkg.name, "=", pkg.version)

    def fetchPackages(self, packages, caching=OPTIONAL, targetdir=None):
        fetcher = self._fetcher
        fetcher.reset()
        fetcher.setCaching(caching)
        if targetdir is None:
            localdir = os.path.join(sysconf.get("data-dir"), "packages/")
            if not os.path.isdir(localdir):
                os.makedirs(localdir)
            fetcher.setLocalDir(localdir, mangle=False)
        else:
            fetcher.setLocalDir(targetdir, mangle=False)
        pkgitems = {}
        for pkg in packages:
            loader = [x for x in pkg.loaders if not x.getInstalled()][0]
            info = loader.getInfo(pkg)
            urls = info.getURLs()
            pkgitems[pkg] = []
            for url in urls:
                pkgitems[pkg].append(fetcher.enqueue(url,
                                                     md5=info.getMD5(url),
                                                     sha=info.getSHA(url),
                                                     size=info.getSize(url),
                                                     validate=info.validate))
        fetcher.run(what="packages")
        failed = fetcher.getFailedSet()
        if failed:
            raise Error, "Failed to download packages:\n" + \
                         "\n".join(["    %s: %s" % (url, failed[url])
                                    for url in failed])
        pkgpaths = {}
        for pkg in packages:
            pkgpaths[pkg] = [item.getTargetPath() for item in pkgitems[pkg]]
        return pkgpaths

    def fetchFiles(self, urllst, what, caching=NEVER, targetdir=None):
        fetcher = self._fetcher
        if targetdir is None:
            localdir = os.path.join(sysconf.get("data-dir"), "tmp/")
            if not os.path.isdir(localdir):
                os.makedirs(localdir)
            fetcher.setLocalDir(localdir, mangle=True)
        else:
            fetcher.setLocalDir(targetdir, mangle=False)
        fetcher.setCaching(caching)
        for url in urllst:
            fetcher.enqueue(url)
        fetcher.run(what=what)
        return fetcher.getSucceededSet(), fetcher.getFailedSet()

    def dumpTransactionURLs(self, trans, output=None):
        changeset = trans.getChangeSet()
        self.dumpURLs([x for x in changeset if changeset[x] is INSTALL])

    def dumpURLs(self, packages, output=None):
        if output is None:
            output = sys.stderr
        urls = []
        for pkg in packages:
            loaders = [x for x in pkg.loaders if not x.getInstalled()]
            if not loaders:
                raise Error, "Package %s is not available for downloading" \
                             % pkg
            info = loaders[0].getInfo(pkg)
            urls.extend(info.getURLs())
        for url in urls:
            print >>output, url

    def downloadTransaction(self, trans, caching=OPTIONAL, confirm=True):
        return self.downloadChangeSet(trans.getChangeSet(), caching, confirm)

    def downloadChangeSet(self, changeset, caching=OPTIONAL, confirm=True):
        if confirm and not iface.confirmChangeSet(changeset):
            return False
        self.fetchPackages([pkg for pkg in changeset
                            if changeset[pkg] is INSTALL], caching)
        return True

    def commitTransaction(self, trans, caching=OPTIONAL, confirm=True):
        return self.commitChangeSet(trans.getChangeSet(), caching, confirm)

    def commitChangeSet(self, changeset, caching=OPTIONAL, confirm=True):
        if confirm and not iface.confirmChangeSet(changeset):
            return False
        pkgpaths = self.fetchPackages([pkg for pkg in changeset
                                       if changeset[pkg] is INSTALL], caching)
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
            pm.commit(pminstall, pmremove, pkgpaths)

        datadir = sysconf.get("data-dir")
        for pkg in pkgpaths:
            for path in pkgpaths[pkg]:
                if path.startswith(datadir):
                    os.unlink(path)

        return True

    def commitTransactionStepped(self, trans, caching=OPTIONAL, confirm=True):
        return self.commitChangeSetStepped(trans.getChangeSet(),
                                           caching, confirm)

    def commitChangeSetStepped(self, changeset, caching=OPTIONAL,
                               confirm=True):
        if confirm and not iface.confirmChangeSet(changeset):
            return False

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

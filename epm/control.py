from epm.elementtree import ElementTree
from epm.fetcher import Fetcher
from epm.cache import Cache
from epm import *
import sys, os
import cPickle

CONFIGFILES = [
    ("~/.epm/config", "~/.epm/"),
    ("/etc/epm.conf", "/var/state/epm"),
]

CACHEFORMAT = 1

class Control:

    def __init__(self, options):
        self._opts = options
        self._root = None
        self._reps = []
        self._cache = Cache()
        self._datadir = None

    def getRepositories(self):
        return self._reps

    def getOptions(self):
        return self._opts

    def getCache(self):
        return self._cache

    def loadCache(self):
        self._cache.load()

    def reloadCache(self):
        self._cache.reload()

    def standardInit(self):
        self.readConfig()
        if 1:
            self.loadRepositories()
            self.acquireRepositories()
            self.loadCache()
        else:
            self.restoreState()
            self.reloadCache()

    def standardFinalize(self):
        #self._cache.reset(True)
        #self.dumpState();
        pass

    def readConfig(self):
        root = None
        opts = self._opts
        if opts.conffile:
            if not os.path.isfile(opts.conffile):
                raise Error, "configuration file not found: "+opts.conffile
            logger.debug("parsing configuration file: "+opts.conffile)
            root = ElementTree.parse(opts.conffile).getroot()
        else:
            for conffile, datadir in CONFIGFILES:
                conffile = os.path.expanduser(conffile)
                if os.path.isfile(conffile):
                    logger.debug("parsing configuration file: "+conffile)
                    root = ElementTree.parse(conffile).getroot()
                    datadir = os.path.expanduser(datadir)
                    logger.debug("data directory set to: "+datadir)
                    self._datadir = datadir
                    break
            else:
                raise Error, "no configuration file found in: " + \
                             " ".join(CONFIGFILES)
        self.root = root

    def importRepository(self, type):
        try:
            xtype = type.replace('-', '_').lower()
            epm_module = __import__("epm.repositories."+xtype)
            reps_module = getattr(epm_module, "repositories")
            rep_module = getattr(reps_module, xtype)
        except (ImportError, AttributeError):
            if self._opts.loglevel == "debug":
                import traceback
                traceback.print_exc()
                sys.exit(1)
            raise Error, "invalid repository type '%s'" % type

        return rep_module.repository

    def loadRepositories(self, name=None):
        for node in self.root.getchildren():
            if node.tag == "repositories":
                for node in node.getchildren():
                    if not name or node.get("name") == name:
                        Repository = self.importRepository(node.get("type"))
                        self._reps.append(Repository(node))

    def acquireRepositories(self):
        fetcher = Fetcher() # XXX
        for rep in self._reps:
            self._cache.removeLoader(rep.getLoader())
            rep.acquire(fetcher)
            self._cache.addLoader(rep.getLoader())

    def dumpState(self):
        if self._datadir:
            filename = os.path.join(self._datadir, "cache.dump")
            file = open(filename, "w")
            cPickle.dump(CACHEFORMAT, file, 2)
            cPickle.dump((self._reps, self._cache), file, 2)
            file.close()

    def restoreState(self):
        if self._datadir:
            try:
                filename = os.path.join(self._datadir, "cache.dump")
                file = open(filename)
                format = cPickle.load(file)
                if format != CACHEFORMAT:
                    return False
                self._reps, self._cache = cPickle.load(file)
                file.close()
            except (IOError, cPickle.UnpicklingError):
                pass
            else:
                return True
        return False

# vim:ts=4:sw=4:et

from cpm.elementtree import ElementTree
from cpm.committer import Committer
from cpm.progress import Progress
from cpm.fetcher import Fetcher
from cpm.cache import Cache
from cpm.const import *
from cpm import *
import sys, os

CONFIGFILES = [
    ("~/.cpm/config", "~/.cpm/"),
    ("/etc/cpm.conf", "/var/state/cpm"),
]

CACHEFORMAT = 1

class Control:

    def __init__(self, options):
        self._progress = Progress()
        self._options = options
        self._config = None
        self._reps = []
        self._cache = Cache()
        self._datadir = None
        self._fetcher = Fetcher()
        self._committer = Committer()

    def getProgress(self):
        return self._progress

    def setProgress(self, prog):
        self._progress = prog

    def getRepositories(self):
        return self._reps

    def getOptions(self):
        return self._options

    def getConfig(self):
        return self._config

    def getCache(self):
        return self._cache

    def getFetcher(self):
        return self._fetcher

    def setFetcher(self):
        self._fetcher = fetcher

    def getCommitter(self):
        return self._committer

    def setCommitter(self, committer):
        self._committer = committer

    def loadCache(self):
        self._cache.setProgress(self._progress)
        self._cache.load()

    def reloadCache(self):
        self._cache.setProgress(self._progress)
        self._cache.reload()

    def update(self):
        self._cache.setProgress(self._progress)
        self._fetcher.setProgress(self._progress)
        self.readConfig()
        self.loadRepositories()
        self._fetcher.setCaching(NEVER)
        self.acquireRepositories()
        self._fetcher.setCaching(OPTIONAL)

    def standardInit(self):
        self._cache.setProgress(self._progress)
        self._fetcher.setProgress(self._progress)
        self.readConfig()
        self.loadRepositories()
        self._fetcher.setCaching(ALWAYS)
        self.acquireRepositories()
        self._fetcher.setCaching(OPTIONAL)
        self.loadCache()

    def standardFinalize(self):
        pass

    def readConfig(self):
        root = None
        opts = self._options
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
        self._config = root

    def importRepository(self, type):
        try:
            xtype = type.replace('-', '_').lower()
            cpm_module = __import__("cpm.repositories."+xtype)
            reps_module = getattr(cpm_module, "repositories")
            rep_module = getattr(reps_module, xtype)
        except (ImportError, AttributeError):
            if self._options.loglevel == "debug":
                import traceback
                traceback.print_exc()
                sys.exit(1)
            raise Error, "invalid repository type '%s'" % type

        return rep_module.repository

    def loadRepositories(self, name=None):
        for node in self._config.getchildren():
            if node.tag == "repositories":
                for node in node.getchildren():
                    if not name or node.get("name") == name:
                        Repository = self.importRepository(node.get("type"))
                        self._reps.append(Repository(node))

    def acquireRepositories(self):
        for rep in self._reps:
            self._cache.removeLoader(rep.getLoader())
            rep.acquire(self._fetcher)
            self._cache.addLoader(rep.getLoader())

    def acquireAndCommit(self, trans):
        committer = self._committer
        committer.setProgress(self._progress)
        committer.setFetcher(self._fetcher)
        committer.acquireAndCommit(trans)

    def acquire(self, trans):
        committer = self._committer
        committer.setProgress(self._progress)
        committer.setFetcher(self._fetcher)
        committer.acquire(trans)

# vim:ts=4:sw=4:et

from cpm import *

class Repository:

    def __init__(self, type, name):
        self._type = type
        self._name = name
        self._loader = None

    def getName(self):
        return self._name

    def getType(self):
        return self._type

    def getLoader(self):
        return self._loader

    def fetch(self, fetcher):
        pass

class RepositoryDataError(Error): pass

def createRepository(type, data):
    try:
        xtype = type.replace('-', '_').lower()
        cpm = __import__("cpm.repositories."+xtype)
        repositories = getattr(cpm, "repositories")
        repository = getattr(repositories, xtype)
    except (ImportError, AttributeError):
        if sysconf.get("log-level") == "debug":
            import traceback
            traceback.print_exc()
            sys.exit(1)
        raise Error, "invalid repository type '%s'" % type
    try:
        repos = repository.create(type, data)
    except RepositoryDataError:
        raise Error, "repository type %s doesn't support %s" % (type, `data`)
    return repos

# vim:ts=4:sw=4:et

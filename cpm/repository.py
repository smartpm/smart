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
        from cpm.const import DEBUG
        if sysconf.get("log-level") == DEBUG:
            import traceback
            traceback.print_exc()
        raise Error, "invalid repository type '%s'" % type
    try:
        return repository.create(type, data)
    except RepositoryDataError:
        raise Error, "repository type %s doesn't support %s" % (type, `data`)

def parseRepositoryDescription(data):
    replst = []
    current = None
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) > 2 and line[0] == "[" and line[-1] == "]":
            if current:
                replst.append(current)
            current = {}
            current["name"] = line[1:-1]
        elif current and not line[0] == "#" and "=" in line:
            key, value = line.split("=")
            current[key.strip().lower()] = value.strip()
    if current:
        replst.append(current)
    return replst

def createRepositoryDescription(rep):
    lines = []
    name = rep.get("name")
    lines.append("[%s]" % name)
    if not name:
        return None
    type = rep.get("type")
    if not type:
        return None
    lines.append("type = %s" % type)
    for key in rep:
        key = key.lower()
        if key not in ("name", "type"):
            lines.append("%s = %s" % (key, rep[key]))
    return "\n".join(lines)

# vim:ts=4:sw=4:et

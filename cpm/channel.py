from cpm import *

class Channel:

    def __init__(self, type, alias, name=None, description=None, priority=0):
        self._type = type
        self._alias = alias
        self._name = name
        self._description = description
        self._priority = priority
        self._loader = None
        self._loadorder = 1000

    def getType(self):
        return self._type

    def getAlias(self):
        return self._alias

    def getName(self):
        return self._name or self._alias

    def getDescription(self):
        return self._description

    def getPriority(self):
        return self._priority

    def getLoader(self):
        return self._loader

    def getLoadOrder(self):
        return self._loadorder

    def __cmp__(self, other):
        if isinstance(other, Channel):
            return cmp(self._loadorder, other._loadorder)
        return -1

    def getFetchSteps(self):
        return 0

    def fetch(self, fetcher, progress):
        pass

class ChannelDataError(Error): pass

def createChannel(type, alias, data):
    try:
        xtype = type.replace('-', '_').lower()
        cpm = __import__("cpm.channels."+xtype)
        channels = getattr(cpm, "channels")
        channel = getattr(channels, xtype)
    except (ImportError, AttributeError):
        from cpm.const import DEBUG
        if sysconf.get("log-level") == DEBUG:
            import traceback
            traceback.print_exc()
        raise Error, "Invalid channel type '%s'" % type
    try:
        return channel.create(type, alias, data)
    except ChannelDataError:
        raise Error, "Channel type %s doesn't support %s" % (type, `data`)

def createChannelDescription(type, alias, data):
    lines = []
    lines.append("[%s]" % alias)
    lines.append("type = %s" % type)
    first = ("name", "description")
    for key in first:
        if key in ("type", "alias"):
            continue
        if key in data:
            lines.append("%s = %s" % (key, data[key]))
    keys = data.keys()
    keys.sort()
    for key in keys:
        if key in ("type", "alias"):
            continue
        if key not in first:
            lines.append("%s = %s" % (key, data[key]))
    return "\n".join(lines)

def parseChannelDescription(data):
    channels = {}
    current = None
    alias = None
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) > 2 and line[0] == "[" and line[-1] == "]":
            if current and "type" not in current:
                raise Error, "Channel '%s' has no type" % alias
            alias = line[1:-1].strip()
            current = {}
            channels[alias] = current
        elif current is not None and not line[0] == "#" and "=" in line:
            key, value = line.split("=")
            current[key.strip().lower()] = value.strip()
    return channels

# vim:ts=4:sw=4:et

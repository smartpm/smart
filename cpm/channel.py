from cpm import *

class Channel:

    def __init__(self, type, alias, name=None, description=None):
        self._type = type
        self._alias = alias
        self._name = name
        self._description = description
        self._loader = None

    def getAlias(self):
        return self._alias

    def getName(self):
        return self._name or self._alias

    def getDescription(self):
        return self._description

    def getType(self):
        return self._type

    def getLoader(self):
        return self._loader

    def fetch(self, fetcher):
        pass

class ChannelDataError(Error): pass

def createChannel(type, data):
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
        return channel.create(type, data)
    except ChannelDataError:
        raise Error, "Channel type %s doesn't support %s" % (type, `data`)

def parseChannelDescription(data):
    channels = []
    current = None
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) > 2 and line[0] == "[" and line[-1] == "]":
            if current:
                channels.append(current)
            current = {}
            current["alias"] = line[1:-1]
        elif current and not line[0] == "#" and "=" in line:
            key, value = line.split("=")
            current[key.strip().lower()] = value.strip()
    if current:
        channels.append(current)
    return channels

def createChannelDescription(channel):
    if "alias" not in channel or "type" not in channel:
        return None
    lines = []
    alias = channel.get("alias")
    lines.append("[%s]" % alias)
    first = ("name", "type", "description")
    for key in first:
        if key == "alias":
            continue
        if key in channel:
            lines.append("%s = %s" % (key, channel[key]))
    keys = channel.keys()
    keys.sort()
    for key in keys:
        if key == "alias":
            continue
        if key not in first:
            lines.append("%s = %s" % (key, channel[key]))
    return "\n".join(lines)

# vim:ts=4:sw=4:et

from cpm import *

class Channel:

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
            current["name"] = line[1:-1]
        elif current and not line[0] == "#" and "=" in line:
            key, value = line.split("=")
            current[key.strip().lower()] = value.strip()
    if current:
        channels.append(current)
    return channels

def createChannelDescription(channel):
    lines = []
    name = channel.get("name")
    lines.append("[%s]" % name)
    if not name:
        return None
    type = channel.get("type")
    if not type:
        return None
    lines.append("type = %s" % type)
    for key in channel:
        key = key.lower()
        if key not in ("name", "type"):
            lines.append("%s = %s" % (key, channel[key]))
    return "\n".join(lines)

# vim:ts=4:sw=4:et

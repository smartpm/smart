from cpm.backends.rpm.header import RPMDBLoader
from cpm.channel import Channel

class RPMDBChannel(Channel):

    def __init__(self, *args):
        Channel.__init__(self, *args)
        self._loadorder = 500

    def fetch(self, fetcher, progress):
        self._loader = RPMDBLoader()
        self._loader.setChannel(self)

def create(type, alias, data):
    name = None
    description = None
    priority = 0
    if isinstance(data, dict):
        name = data.get("name")
        description = data.get("description")
        priority = data.get("priority", 0)
    elif getattr(data, "tag", None) == "channel":
        for n in data.getchildren():
            if n.tag == "name":
                name = n.text
            elif n.tag == "description":
                description = n.text
            elif n.tag == "priority":
                priority = n.text
    else:
        raise ChannelDataError
    try:
        priority = int(priority)
    except ValueError:
        raise Error, "Invalid priority"
    return RPMDBChannel(type, alias, name, description, priority)

# vim:ts=4:sw=4:et

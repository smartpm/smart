from cpm.backends.rpm.header import RPMDBLoader
from cpm.channel import Channel

class RPMDBChannel(Channel):

    def fetch(self, fetcher):
        self._loader = RPMDBLoader()
        self._loader.setChannel(self)

def create(ctype, data):
    alias = None
    name = None
    description = None
    if type(data) is dict:
        alias = data.get("alias")
        name = data.get("name")
        description = data.get("description")
    elif hasattr(data, "tag") and data.tag == "channel":
        node = data
        alias = node.get("alias")
        for n in node.getchildren():
            if n.tag == "name":
                name = n.text
            elif n.tag == "description":
                description = n.text
    else:
        raise ChannelDataError
    if not alias:
        raise Error, "Channel of type '%s' has no alias" % ctype
    return RPMDBChannel(ctype, alias, name, description)

# vim:ts=4:sw=4:et

from cpm.backends.rpm.header import RPMDBLoader
from cpm.channel import Channel

class RPMDBChannel(Channel):

    def fetch(self, fetcher):
        self._loader = RPMDBLoader()
        self._loader.setChannel(self)

def create(ctype, data):
    name = None
    if type(data) is dict:
        name = data.get("name")
    elif hasattr(data, "tag") and data.tag == "channel":
        name = data.get("name")
    else:
        raise ChannelDataError
    if not name:
        raise Error, "channel of type '%s' has no name" % ctype
    return RPMDBChannel(ctype, name)

# vim:ts=4:sw=4:et

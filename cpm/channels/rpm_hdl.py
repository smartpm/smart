from cpm.backends.rpm.header import RPMHeaderListLoader
from cpm.const import SUCCEEDED, FAILED
from cpm.channel import Channel
from cpm import *
import posixpath

class RPMHeaderListChannel(Channel):

    def __init__(self, type, alias, name, description, hdlurl, baseurl):
        Channel.__init__(self, type, alias, name, description)
        
        self._hdlurl = hdlurl
        self._baseurl = baseurl

    def getFetchSteps(self):
        return 1

    def fetch(self, fetcher, progress):
        fetcher.reset()
        item = fetcher.enqueue(self._hdlurl, uncomp=True)
        fetcher.run(progress=progress)
        if item.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            self._loader = RPMHeaderListLoader(localpath, self._baseurl)
            self._loader.setChannel(self)
        else:
            iface.warning("Failed acquiring information for '%s':" %
                          self._alias)
            iface.warning("%s: %s" % (item.getURL(), item.getFailedReason()))

def create(ctype, data):
    alias = None
    name = None
    description = None
    hdlurl = None
    baseurl = None
    if type(data) is dict:
        alias = data.get("alias")
        name = data.get("name")
        description = data.get("description")
        hdlurl = data.get("hdlurl")
        baseurl = data.get("baseurl")
    elif hasattr(data, "tag") and data.tag == "channel":
        node = data
        alias = node.get("alias")
        for n in node.getchildren():
            if n.tag == "name":
                name = n.text
            elif n.tag == "description":
                description = n.text
            elif n.tag == "hdlurl":
                hdlurl = n.text
            elif n.tag == "baseurl":
                baseurl = n.text
    else:
        raise ChannelDataError
    if not alias:
        raise Error, "Channel of type '%s' has no alias" % ctype
    if not hdlurl:
        raise Error, "Channel '%s' has no hdlurl" % alias
    if not baseurl:
        raise Error, "Channel '%s' has no baseurl" % alias
    return RPMHeaderListChannel(ctype, alias, name, description,
                                hdlurl, baseurl)

# vim:ts=4:sw=4:et

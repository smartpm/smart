from cpm.backends.rpm.header import RPMHeaderListLoader
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
        fetcher.enqueue(self._hdlurl, uncomp=True)
        fetcher.run(progress=progress)
        failed = fetcher.getFailedSet()
        if failed:
            iface.warning("Failed acquiring header list for '%s': %s" %
                          (self._alias, failed[self._hdlurl]))
            iface.debug("%s: %s" % (self._hdlurl, failed[self._hdlurl]))
        else:
            localpath = fetcher.getSucceeded(self._hdlurl)
            self._loader = RPMHeaderListLoader(localpath, self._baseurl)
            self._loader.setChannel(self)

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

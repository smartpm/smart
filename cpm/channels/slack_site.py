from cpm.backends.slack.loader import SlackSiteLoader
from cpm.channel import Channel, ChannelDataError
from cpm.const import SUCCEEDED, FAILED
from cpm import *
import posixpath

class SlackSiteChannel(Channel):

    def __init__(self, type, alias, name, description, baseurl):
        Channel.__init__(self, type, alias, name, description)
        self._baseurl = baseurl

    def getFetchSteps(self):
        return 1

    def fetch(self, fetcher, progress):

        fetcher.reset()

        # Fetch packages file
        url = posixpath.join(self._baseurl, "PACKAGES.TXT")
        item = fetcher.enqueue(url)
        fetcher.run(progress=progress)
        if item.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            self._loader = SlackSiteLoader(localpath, self._baseurl)
            self._loader.setChannel(self)
        else:
            iface.warning("Failed acquiring information for '%s':" %
                          self._alias)
            iface.warning("%s: %s" % (item.getURL(), item.getFailedReason()))

def create(ctype, data):
    alias = None
    name = None
    description = None
    baseurl = None
    if type(data) is dict:
        alias = data.get("alias")
        name = data.get("name")
        description = data.get("description")
        baseurl = data.get("baseurl")
    elif hasattr(data, "tag") and data.tag == "channel":
        node = data
        alias = node.get("alias")
        for n in node.getchildren():
            if n.tag == "name":
                name = n.text
            elif n.tag == "description":
                description = n.text
            elif n.tag == "baseurl":
                baseurl = n.text
    else:
        raise ChannelDataError
    if not alias:
        raise Error, "Channel of type '%s' has no alias" % ctype
    if not baseurl:
        raise Error, "Channel '%s' has no baseurl" % alias
    return SlackSiteChannel(ctype, alias, name, description, baseurl)

# vim:ts=4:sw=4:et

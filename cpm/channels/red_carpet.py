from cpm.backends.rpm.redcarpet import RPMRedCarpetLoader
from cpm.const import SUCCEEDED, FAILED
from cpm.channel import Channel
from cpm import *
import posixpath

class RPMRedCarpetChannel(Channel):

    def __init__(self, type, alias, name, description,
                 baseurl, packageinfourl):
        Channel.__init__(self, type, alias, name, description)
        self._baseurl = baseurl
        self._packageinfourl = packageinfourl

    def getFetchSteps(self):
        return 1

    def fetch(self, fetcher, progress):

        pkginfourl = self._packageinfourl
        if not pkginfourl:
            pkginfourl = posixpath.join(self._baseurl, "packageinfo.xml.gz")

        fetcher.reset()
        item = fetcher.enqueue(pkginfourl, uncomp=True)
        fetcher.run(progress=progress)

        if item.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            self._loader = RPMRedCarpetLoader(localpath, self._baseurl)
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
        packageinfourl = data.get("packageinfourl")
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
            elif n.tag == "packageinfourl":
                packageinfourl = n.text
    else:
        raise ChannelDataError
    if not alias:
        raise Error, "Channel of type '%s' has no alias" % ctype
    if not baseurl:
        raise Error, "Channel '%s' has no baseurl" % alias
    return RPMRedCarpetChannel(ctype, alias, name, description,
                               baseurl, packageinfourl)

# vim:ts=4:sw=4:et

from gepeto.backends.rpm.redcarpet import RPMRedCarpetLoader
from gepeto.const import SUCCEEDED, FAILED
from gepeto.channel import Channel
from gepeto import *
import posixpath

class RPMRedCarpetChannel(Channel):

    def __init__(self, baseurl, packageinfourl, *args):
        Channel.__init__(self, *args)
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

def create(type, alias, data):
    name = None
    description = None
    priority = 0
    baseurl = None
    if isinstance(data, dict):
        name = data.get("name")
        description = data.get("description")
        priority = data.get("priority", 0)
        baseurl = data.get("baseurl")
        packageinfourl = data.get("packageinfourl")
    elif getattr(data, "tag", None) == "channel":
        for n in data.getchildren():
            if n.tag == "name":
                name = n.text
            elif n.tag == "description":
                description = n.text
            elif n.tag == "priority":
                priority = n.text
            elif n.tag == "baseurl":
                baseurl = n.text
            elif n.tag == "packageinfourl":
                packageinfourl = n.text
    else:
        raise ChannelDataError
    if not baseurl:
        raise Error, "Channel '%s' has no baseurl" % alias
    try:
        priority = int(priority)
    except ValueError:
        raise Error, "Invalid priority"
    return RPMRedCarpetChannel(baseurl, packageinfourl,
                               type, alias, name, description, priority)

# vim:ts=4:sw=4:et

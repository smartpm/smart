from cpm.backends.rpm.metadata import RPMMetaDataLoader
from cpm.util.elementtree import ElementTree
from cpm.channel import Channel
from cpm import *
import posixpath

NS = "{http://linux.duke.edu/metadata/repo}"
DATA = NS+"data"
LOCATION = NS+"location"
CHECKSUM = NS+"checksum"
OPENCHECKSUM = NS+"open-checksum"

class RPMMetaDataChannel(Channel):

    def __init__(self, type, alias, name, description, baseurl):
        Channel.__init__(self, type, alias, name, description)
        self._baseurl = baseurl

    def fetch(self, fetcher):

        fetcher.reset()

        #root = ElementTree.parse(
        """
        """#"""

        fetcher.reset()
        repomd = posixpath.join(self._baseurl, "repodata/repomd.xml")
        fetcher.enqueue(repomd)
        fetcher.run("repository metadata for '%s'" % self._alias)

        failed = fetcher.getFailed(repomd)
        info = {}
        if failed:
            iface.warning("Failed acquiring repository metadata for '%s': %s" %
                          (self._alias, failed))
            iface.debug("%s: %s" % (repomd, failed))
            return

        root = ElementTree.parse(fetcher.getSucceeded(repomd)).getroot()
        for node in root.getchildren():
            if node.tag != DATA:
                continue
            type = node.get("type")
            info[type] = {}
            for subnode in node.getchildren():
                if subnode.tag == LOCATION:
                    info[type]["url"] = \
                        posixpath.join(self._baseurl, subnode.get("href"))
                if subnode.tag == CHECKSUM:
                    info[type][subnode.get("type")] = subnode.text
                if subnode.tag == OPENCHECKSUM:
                    info[type]["uncomp_"+subnode.get("type")] = \
                        subnode.text

        if "primary" not in info:
            iface.warning("Primary information not found in repository "
                          "metadata for '%s'" % self._alias)
            return

        fetcher.reset()
        primaryurl = info["primary"]["url"]
        urlmap = {primaryurl: "primary"}
        fetcher.enqueue(primaryurl,
                        md5=info["primary"].get("md5"),
                        uncomp_md5=info["primary"].get("uncomp_md5"),
                        uncomp=True)
        fetcher.run("information for '%s'" % self._alias)

        succeeded = fetcher.getSucceededSet()
        if primaryurl in succeeded:
            filename = succeeded.get(primaryurl)
            if filename:
                self._loader = RPMMetaDataLoader(filename, self._baseurl)
                self._loader.setChannel(self)

        failed = fetcher.getFailedSet()
        if failed:
            iface.warning("Failed acquiring information for '%s': %s" %
                          (self._alias, ", ".join(["%s (%s)" %
                                                   (urlmap[x], failed[x])
                                                   for x in failed])))
            if sysconf.get("log-level") >= DEBUG:
                for url in failed:
                    iface.debug("%s: %s" % (url, failed[url]))

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
    return RPMMetaDataChannel(ctype, alias, name, description, baseurl)

# vim:ts=4:sw=4:et

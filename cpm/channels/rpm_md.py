from cpm.backends.rpm.metadata import RPMMetaDataLoader
from cpm.util.elementtree import ElementTree
from cpm.const import SUCCEEDED, FAILED
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

    def getFetchSteps(self):
        return 2

    def fetch(self, fetcher, progress):

        fetcher.reset()
        repomd = posixpath.join(self._baseurl, "repodata/repomd.xml")
        item = fetcher.enqueue(repomd)
        fetcher.run(progress=progress)

        if item.getStatus() == FAILED:
            iface.warning("Failed acquiring information for '%s':" %
                          self._alias)
            iface.warning("%s: %s" % (item.getURL(), item.getFailedReason()))
            progress.add(1)
            return

        info = {}
        root = ElementTree.parse(item.getTargetPath()).getroot()
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
        item = fetcher.enqueue(info["primary"]["url"],
                               md5=info["primary"].get("md5"),
                               uncomp_md5=info["primary"].get("uncomp_md5"),
                               uncomp=True)
        fetcher.run(progress=progress)

        if item.getStatus() == SUCCEEDED:
            localpath = item.getTargetPath()
            self._loader = RPMMetaDataLoader(localpath, self._baseurl)
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
    return RPMMetaDataChannel(ctype, alias, name, description, baseurl)

# vim:ts=4:sw=4:et

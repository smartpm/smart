from cpm.backends.rpm.header import URPMILoader
from cpm.channel import Channel
from cpm.const import ALWAYS
from cpm import *
import posixpath
import os

class URPMIChannel(Channel):

    def __init__(self, type, alias, name, description, hdlurl, baseurl):
        Channel.__init__(self, type, alias, name, description)
        
        self._hdlurl = hdlurl
        self._baseurl = baseurl

    def getFetchSteps(self):
        return 2

    def fetch(self, fetcher, progress):

        fetcher.reset()

        url = posixpath.join(self._baseurl, "MD5SUM")
        fetcher.enqueue(url)
        fetcher.run(progress=progress)
        failed = fetcher.getFailed(url)
        hdlmd5 = None
        if failed:
            iface.warning("Failed acquiring digest file for '%s': %s" %
                          (self._alias, failed))
            iface.debug("%s: %s" % (url, failed))
        else:
            basename = posixpath.basename(self._hdlurl)
            for line in open(fetcher.getSucceeded(url)):
                md5, name = line.split()
                if name == basename:
                    hdlmd5 = md5
                    break

        fetcher.reset()
        fetcher.enqueue(self._hdlurl, md5=hdlmd5, uncomp=True)
        fetcher.run(progress=progress)
        failed = fetcher.getFailedSet()
        if failed:
            iface.warning("Failed acquiring header list for '%s': %s" %
                          (self._alias, failed[self._hdlurl]))
            iface.debug("%s: %s" % (self._hdlurl, failed[self._hdlurl]))
        else:
            localpath = fetcher.getSucceeded(self._hdlurl)
            if localpath.endswith(".cz"):
                if (not os.path.isfile(localpath[:-3]) or
                    fetcher.getCaching() != ALWAYS):
                    linkpath = localpath[:-2]+"gz"
                    if os.path.isfile(linkpath):
                        os.unlink(linkpath)
                    os.symlink(localpath, linkpath)
                    uncompressor = fetcher.getUncompressor()
                    uncomphandler = uncompressor.getHandler(linkpath)
                    try:
                        uncomphandler.uncompress(linkpath)
                    except Error, e:
                        # cz file has trailing information which breaks
                        # current gzip module logic.
                        if "Not a gzipped file" not in e[0]:
                            os.unlink(linkpath)
                            raise
                    os.unlink(linkpath)
                localpath = localpath[:-3]
            self._loader = URPMILoader(localpath, self._baseurl)
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
    return URPMIChannel(ctype, alias, name, description, hdlurl, baseurl)

# vim:ts=4:sw=4:et

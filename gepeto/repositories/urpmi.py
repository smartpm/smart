from cpm.backends.rpm.header import URPMILoader
from cpm.repository import Repository
from cpm.const import ALWAYS
from cpm import *
import posixpath
import os

class URPMIRepository(Repository):

    def __init__(self, type, name, hdlurl, baseurl):
        Repository.__init__(self, type, name)
        
        self._hdlurl = hdlurl
        self._baseurl = baseurl

    def fetch(self, fetcher):

        fetcher.reset()

        url = posixpath.join(self._baseurl, "MD5SUM")
        fetcher.enqueue(url)
        fetcher.run("digest file for '%s'" % self._name)
        failed = fetcher.getFailed(url)
        hdlmd5 = None
        if failed:
            iface.warning("failed acquiring digest file for '%s': %s" %
                          (self._name, failed))
            iface.debug("%s: %s" % (url, failed))
        else:
            basename = posixpath.basename(self._hdlurl)
            for line in open(fetcher.getSucceeded(url)):
                md5, name = line.split()
                if name == basename:
                    hdlmd5 = md5
                    break

        fetcher.reset()
        fetcher.enqueue(self._hdlurl)
        fetcher.setInfo(self._hdlurl, md5=hdlmd5, uncomp=True)
        fetcher.run("header list for '%s'" % self._name)
        failed = fetcher.getFailedSet()
        if failed:
            iface.warning("failed acquiring header list for '%s': %s" %
                          (self._name, failed[self._hdlurl]))
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
            self._loader.setRepository(self)

def create(reptype, data):
    name = None
    hdlurl = None
    baseurl = None
    if type(data) is dict:
        name = data.get("name")
        hdlurl = data.get("hdlurl")
        baseurl = data.get("baseurl")
    elif hasattr(data, "tag") and data.tag == "repository":
        node = data
        name = node.get("name")
        for n in node.getchildren():
            if n.tag == "hdlurl":
                hdlurl = n.text
            elif n.tag == "baseurl":
                baseurl = n.text
    else:
        raise RepositoryDataError
    if not name:
        raise Error, "repository of type '%s' has no name" % reptype
    if not hdlurl:
        raise Error, "repository '%s' has no hdlurl" % name
    if not baseurl:
        raise Error, "repository '%s' has no baseurl" % name
    return URPMIRepository(reptype, name, hdlurl, baseurl)

# vim:ts=4:sw=4:et

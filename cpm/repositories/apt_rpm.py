from cpm.backends.rpm.header import RPMPackageListLoader
from cpm.repository import Repository, RepositoryDataError
from cpm.cache import LoaderSet
from cpm.const import DEBUG
from cpm import *
import posixpath

class APTRPMRepository(Repository):

    def __init__(self, type, name, baseurl, comps):
        Repository.__init__(self, type, name)
        
        self._baseurl = baseurl
        self._comps = comps

        self._loader = LoaderSet()

    def fetch(self, fetcher):
        fetcher.reset()
        urlcomp = {}
        for comp in self._comps:
            url = posixpath.join(self._baseurl, "base/pkglist."+comp)
            urlcomp[url] = comp
            fetcher.enqueue(url)
        fetcher.run("package lists for '%s'" % self._name)
        succeeded = fetcher.getSucceededSet()
        for url in urlcomp:
            filename = succeeded.get(url)
            if filename:
                loader = RPMPackageListLoader(filename, self._baseurl)
                loader.setRepository(self)
                self._loader.append(loader)
        failed = fetcher.getFailedSet()
        if failed:
            logger.warning("failed acquiring pkglists for '%s': %s" %
                           (self._name, ", ".join(["%s (%s)" %
                                                   (urlcomp[x], failed[x])
                                                   for x in failed])))
            if sysconf.get("log-level") >= DEBUG:
                for url in failed:
                    logger.debug("%s: %s" % (url, failed[url]))

def create(type, data):
    if hasattr(data, "tag") and data.tag == "repository":
        node = data
        name = node.get("name")
        if not name:
            raise Error, "repository of type '%s' has no name" % type
        comps = None
        baseurl = None
        for n in node.getchildren():
            if n.tag == "baseurl":
                baseurl = n.text
            elif n.tag == "components":
                comps = n.text.split()
        if not baseurl:
            raise Error, "repository '%s' has no baseurl" % name
        if not comps:
            raise Error, "repository '%s' has no components" % name
        return APTRPMRepository(type, name, baseurl, comps)
    else:
        raise RepositoryDataError

# vim:ts=4:sw=4:et

from cpm.backends.rpm.header import RPMPackageListLoader
from cpm.repository import Repository
from cpm.cache import LoaderSet
from cpm import *
import posixpath

class APTRPMRepository(Repository):

    def __init__(self, node):
        Repository.__init__(self, node)
        
        self._baseurl = None
        self._comps = None
        self._loader = LoaderSet()

        for n in node.getchildren():
            if n.tag == "baseurl":
                self._baseurl = n.text
            elif n.tag == "components":
                self._comps = n.text.split()

        if not self._baseurl:
            raise Error, "no baseurl found in repository '%s'" % self._name
        elif not self._comps:
            raise Error, "no components found in repository '%s'" % self._name

    def acquire(self, fetcher):
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
                self._loader.append(loader)
        failed = fetcher.getFailedSet()
        if failed:
            logger.warning("unable to find pkglists for components: " +
                           ", ".join([urlcomp[x] for x in failed]))

repository = APTRPMRepository

# vim:ts=4:sw=4:et

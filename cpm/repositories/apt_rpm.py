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

        # Fetch release file
        fetcher.reset()
        url = posixpath.join(self._baseurl, "base/release")
        fetcher.enqueue(url)
        fetcher.run("release file for '%s'" % self._name)
        failed = fetcher.getFailed(url)
        if failed:
            logger.warning("failed acquiring release file for '%s': %s" %
                           (self._name, failed))
            logger.debug("%s: %s" % (url, failed))
            return

        # Parse release file
        md5sum = {}
        started = False
        for line in open(fetcher.getSucceeded(url)):
            if not started:
                if line.startswith("MD5Sum:"):
                    started = True
            elif not line.startswith(" "):
                break
            else:
                try:
                    md5, size, path = line.split()
                except ValueError:
                    pass
                else:
                    md5sum[path] = (md5, int(size))

        # Fetch package lists
        fetcher.reset()
        urlcomp = {}
        for comp in self._comps:
            pkglist = "base/pkglist."+comp
            url = posixpath.join(self._baseurl, pkglist)
            urlcomp[url] = comp
            try:
                md5, size = md5sum[pkglist]
            except KeyError:
                logger.warning("component '%s' is not in release file" % comp)
            else:
                fetcher.enqueue(url)
                fetcher.setInfo(url, size=size, md5=md5)
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

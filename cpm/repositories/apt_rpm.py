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
            iface.warning("failed acquiring release file for '%s': %s" %
                          (self._name, failed))
            iface.debug("%s: %s" % (url, failed))
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
            if pkglist+".bz2" in md5sum:
                upkglist = pkglist
                pkglist += ".bz2"
                url += ".bz2"
            elif pkglist+".gz" in md5sum:
                upkglist = pkglist
                pkglist += ".gz"
                url += ".gz"
            elif pkglist not in md5sum:
                iface.warning("component '%s' is not in release file" % comp)
                continue
            else:
                upkglist = None
            urlcomp[url] = comp
            fetcher.enqueue(url)
            info = {"uncomp": True}
            info["md5"], info["size"] = md5sum[pkglist]
            if upkglist:
                info["uncomp_md5"], info["uncomp_size"] = md5sum[upkglist]
            fetcher.setInfo(url, **info)
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
            iface.warning("failed acquiring pkglists for '%s': %s" %
                          (self._name, ", ".join(["%s (%s)" %
                                                   (urlcomp[x], failed[x])
                                                   for x in failed])))
            if sysconf.get("log-level") >= DEBUG:
                for url in failed:
                    iface.debug("%s: %s" % (url, failed[url]))

def create(reptype, data):
    name = None
    baseurl = None
    comps = None
    if type(data) is dict:
        name = data.get("name")
        baseurl = data.get("baseurl")
        comps = (data.get("components") or "").split()
    elif hasattr(data, "tag") and data.tag == "repository":
        node = data
        name = node.get("name")
        for n in node.getchildren():
            if n.tag == "baseurl":
                baseurl = n.text
            elif n.tag == "components":
                comps = n.text.split()
    else:
        raise RepositoryDataError
    if not name:
        raise Error, "repository of type '%s' has no name" % reptype
    if not baseurl:
        raise Error, "repository '%s' has no baseurl" % name
    if not comps:
        raise Error, "repository '%s' has no components" % name
    return APTRPMRepository(reptype, name, baseurl, comps)

# vim:ts=4:sw=4:et

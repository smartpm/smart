from epm.cache import Loader, PackageInfo
from epm.backends.rpm import *
import posixpath
import rpm

CRPMTAG_FILENAME          = 1000000
CRPMTAG_FILESIZE          = 1000001
CRPMTAG_MD5               = 1000005
CRPMTAG_SHA1              = 1000006

CRPMTAG_DIRECTORY         = 1000010
CRPMTAG_BINARY            = 1000011

CRPMTAG_UPDATE_SUMMARY    = 1000020
CRPMTAG_UPDATE_IMPORTANCE = 1000021
CRPMTAG_UPDATE_DATE       = 1000022
CRPMTAG_UPDATE_URL        = 1000023

class RPMHeaderPackageInfo(PackageInfo):

    def __init__(self, package, loader, header):
        PackageInfo.__init__(self, package)
        self._loader = loader
        self._h = header

    def getDescription(self):
        return self._h[rpm.RPMTAG_DESCRIPTION]

    def getSummary(self):
        return self._h[rpm.RPMTAG_SUMMARY]

    def getFileList(self):
        return self._h[rpm.RPMTAG_OLDFILENAMES]

    def getURL(self):
        url = self._loader.getURL()
        if url:
            url = posixpath.join(url, self._loader.getFileName(self))
        return url

    def getHeader(self):
        return self._h

class RPMHeaderLoader(Loader):
 
    COMPFLAGS = rpm.RPMSENSE_EQUAL|rpm.RPMSENSE_GREATER|rpm.RPMSENSE_LESS

    COMPMAP = { rpm.RPMSENSE_EQUAL:   "=",
                rpm.RPMSENSE_LESS:    "<",
                rpm.RPMSENSE_GREATER: ">",
                rpm.RPMSENSE_EQUAL|rpm.RPMSENSE_LESS:    "<=",
                rpm.RPMSENSE_EQUAL|rpm.RPMSENSE_GREATER: ">=" }

    def getHeaders(self):
        return []

    def reset(self):
        Loader.reset(self)
        self._offsets = {}

    def load(self):
        CM = self.COMPMAP
        CF = self.COMPFLAGS
        Pkg = RPMPackage
        Prv = RPMProvides
        NPrv = RPMNameProvides
        Req = RPMRequires
        Obs = RPMObsoletes
        Cnf = RPMConflicts
        for h, offset in self.getHeaders():

            name = h[1000] # RPMTAG_NAME
            epoch = h[1003] # RPMTAG_EPOCH
            if epoch is not None:
                # RPMTAG_VERSION, RPMTAG_RELEASE
                version = "%s:%s-%s" % (epoch, h[1001], h[1002])
            else:
                # RPMTAG_VERSION, RPMTAG_RELEASE
                version = "%s-%s" % (h[1001], h[1002])

            n = h[1047] # RPMTAG_PROVIDENAME
            v = h[1113] # RPMTAG_PROVIDEVERSION
            prvdict = {}
            for i in range(len(n)):
                ni = n[i]
                if not ni.startswith("config("):
                    vi = v[i]
                    if ni == name and vi == version:
                        prvdict[(NPrv, n[i], v[i] or None)] = True
                    else:
                        prvdict[(Prv, n[i], v[i] or None)] = True
            prvargs = prvdict.keys()

            n = h[1049] # RPMTAG_REQUIRENAME
            if n:
                f = h[1048] # RPMTAG_REQUIREFLAGS
                v = h[1050] # RPMTAG_REQUIREVERSION
                reqdict = {}
                for i in range(len(n)):
                    ni = n[i]
                    if ni[:7] not in ("rpmlib(", "config("):
                        vi = v[i] or None
                        r = CM.get(f[i]&CF)
                        if ((r is not None and r != "=") or
                            ((Prv, ni, vi) not in prvdict)):
                            reqdict[(Req, ni, vi, r)] = True
                reqargs = reqdict.keys()
            else:
                reqargs = None

            n = h[1090] # RPMTAG_OBSOLETENAME
            if n:
                f = h[1114] # RPMTAG_OBSOLETEFLAGS
                v = h[1115] # RPMTAG_OBSOLETEVERSION
                obsargs = [(Obs, n[i], v[i] or None, CM.get(f[i]&CF))
                           for i in range(len(n))]
                obsargs.append((Obs, name, version, '<'))
            else:
                obsargs = [(Obs, name, version, '<')]

            n = h[1054] # RPMTAG_CONFLICTNAME
            if n:
                f = h[1053] # RPMTAG_CONFLICTFLAGS
                v = h[1055] # RPMTAG_CONFLICTVERSION
                cnfargs = [(Cnf, n[i], v[i] or None, CM.get(f[i]&CF))
                           for i in range(len(n))]
            else:
                cnfargs = None

            pkg = self.newPackage((Pkg, name, version),
                                  prvargs, reqargs, obsargs, cnfargs)
            pkg.loaderinfo[self] = offset
            self._offsets[offset] = pkg

class RPMHeaderListLoader(RPMHeaderLoader):

    def __init__(self, filename, baseurl):
        RPMHeaderLoader.__init__(self)
        self._filename = filename
        self._baseurl = baseurl

    def getHeaders(self):
        file = open(self._filename)
        h, offset = rpm.readHeaderFromFD(file.fileno())
        while h:
            yield h, offset
            h, offset = rpm.readHeaderFromFD(file.fileno())
        file.close()

    def getInfo(self, pkg):
        file = open(self._filename)
        file.seek(pkg.loaderinfo[self])
        h, offset = rpm.readHeaderFromFD(file.fileno())
        info = RPMHeaderPackageInfo(pkg, self, h)
        file.close()
        return info

    def getURL(self):
        return self._baseurl

    def getFileName(self, info):
        h = info._h
        return "%s-%s-%s.%s.rpm" % (h[rpm.RPMTAG_NAME],
                                    h[rpm.RPMTAG_VERSION],
                                    h[rpm.RPMTAG_RELEASE],
                                    h[rpm.RPMTAG_ARCH])

    def loadFileProvides(self, fndict):
        file = open(self._filename)
        h, offset = rpm.readHeaderFromFD(file.fileno())
        while h:
            for fn in h[1027]: # RPMTAG_OLDFILENAMES
                if fn in fndict:
                    self.newProvides(self._offsets[offset], RPMProvides, fn)
            h, offset = rpm.readHeaderFromFD(file.fileno())
        file.close()

class RPMPackageListLoader(RPMHeaderListLoader):

    def getFileName(self, info):
        h = info._h
        filename = h[CRPMTAG_FILENAME]
        if not filename:
            raise Error, "package list with no CRPMTAG_FILENAME tag"
        directory = h[CRPMTAG_DIRECTORY]
        if directory:
            filename = posixpath.join(directory, filename)
        return filename

class RPMDBLoader(RPMHeaderLoader):

    def __init__(self):
        RPMHeaderLoader.__init__(self)
        self.setInstalled(True)

    def getHeaders(self):
        ts = rpm.ts()
        mi = ts.dbMatch()
        h = mi.next()
        while h:
            if h[1000] != "gpg-pubkey": # RPMTAG_NAME
                yield h, mi.instance()
            h = mi.next()

    def getInfo(self, pkg):
        ts = rpm.ts()
        mi = ts.dbMatch(0, pkg.loaderinfo[self])
        return RPMHeaderPackageInfo(pkg, self, mi.next())

    def getURL(self):
        return None

    def getFileName(self, info):
        return None

    def loadFileProvides(self, fndict):
        ts = rpm.ts()
        for fn in fndict.keys():
            mi = ts.dbMatch(1117, fn) # RPMTAG_BASENAMES
            h = mi.next()
            while h:
                self.newProvides(self._offsets[mi.instance()], RPMProvides, fn)
                h = mi.next()

class RPMFileLoader(RPMHeaderLoader):

    def __init__(self, filename):
        RPMHeaderLoader.__init__(self)
        self._filename = filename

    def getHeaders(self):
        file = open(self._filename)
        ts = rpm.ts()
        h = ts.hdrFromFdno(file.fileno())
        file.close()
        return [(h, 0)]

    def getInfo(self, pkg):
        file = open(self._filename)
        ts = rpm.ts()
        h = ts.hdrFromFdno(file.fileno())
        info = RPMHeaderPackageInfo(pkg, self, h)
        file.close()
        return info

    def getURL(self):
        return "file://"

    def getFileName(self, info):
        return self._filename

    def loadFileProvides(self, fndict):
        file = open(self._filename)
        ts = rpm.ts()
        h = ts.hdrFromFdno(file.fileno())
        for fn in h[1027]: # RPMTAG_OLDFILENAMES
            if fn in fndict:
                self.newProvides(self._offsets[offset], RPMProvides, fn)
        file.close()

try:
    import psyco
except ImportError:
    pass
else:
    psyco.bind(RPMHeaderLoader.load)
    psyco.bind(RPMDBLoader.loadFileProvides)
    psyco.bind(RPMHeaderListLoader.loadFileProvides)
    psyco.bind(RPMFileLoader.loadFileProvides)

# vim:ts=4:sw=4:et

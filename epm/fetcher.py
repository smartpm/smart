from epm.progress import Progress
from epm import *
import tempfile
import urllib
import string
import os

(
STOPPED,
RUNNING,
FAILED,
SUCCEEDED,
) = range(1,5)

class FetcherFeedback:

    def starting(self, handler=None):
        pass

    def finished(self, handler=None):
        pass

    def error(self, handler, msg):
        pass

class Fetcher(object):

    _registry = {}

    def __init__(self):
        self._feedback = FetcherFeedback()
        self._progress = Progress()
        self._cachedir = tempfile.gettempdir()
        self._cachemangle = False
        self._usecache = True
        self._cahceonly = False
        self._parallel = 1

    def getFeedback(self):
        return self._feedback

    def setFeedback(self, feedback):
        self._feedback = feedback

    def getProgress(self):
        return self._progress

    def setProgress(self, prog):
        self._progress = prog

    def getUseCache(self, flag):
        return self._usecache

    def setUseCache(self, flag):
        self._usecache = flag

    def getCacheOnly(self):
        return self._cacheonly

    def setCacheOnly(self, flag):
        self._cacheonly = flag

    def setCacheDir(self, cachedir, mangle=False):
        self._cachedir = cachedir
        self._cachemangle = mangle

    def getCachePath(self, url):
        if self._cachemangle:
            filename = url.replace("/", "_")
        else:
            scheme, selector = urllib.splittype(url)
            host, path = urllib.splithost(selector)
            path, query = urllib.splitquery(path)
            path = urllib.unquote(path)
            filename = os.path.basename(path)
        filename = os.path.join(self._cachedir, filename)
        return filename

    def setParallel(self, num):
        self._parallel = num

    def get(self, urllst, what):
        acquired = {}
        failed = {}
        self._feedback.starting()
        prog = self._progress
        prog.reset()
        prog.setTopic("Fetching %s..." % what)
        prog.set(0, len(urllst))
        retries = {}
        while urllst:
            url = urllst.pop()

            handler = self.buildHandler(url)
            if self._cacheonly:
                handler.getCached()
                prog.add(1)
            else:
                if self._usecache:
                    handler.getCached()
                if not self._usecache or handler.getStatus() == FAILED:
                    handler.get()
                    if handler.getStatus() == FAILED:
                        if retries.setdefault(url, 3) > 0:
                            retries[url] -= 1
                            urllst.insert(0, url)
                            continue
                        else:
                            prog.add(1)
                else:
                    prog.add(1)
            if handler.getStatus() == SUCCEEDED:
                acquired[url] = handler.getFileName()
            else:
                logger.debug("failed to acquire: "+url)
                failed[url] = True
        self._feedback.finished()
        return acquired, failed

    def setHandler(self, scheme, klass):
        self._registry[scheme] = klass
    setHandler = classmethod(setHandler)

    def getHandler(self, scheme, klass):
        return self._registry.get(scheme)
    getHandler = classmethod(getHandler)

    def buildHandler(self, url):
        type, selector = urllib.splittype(url)
        klass = self._registry.get(type)
        if not klass:
            raise Error, "unsupported scheme: %s" % type
        handler = klass(self, url, self._progress)
        return handler

class Handler(object):
    def __init__(self, fetcher, url, progress):
        self._fetcher = fetcher
        self._url = url
        self._progress = progress
        self._filename = None
        self._status = STOPPED

    def error(self, message):
        self._progress.setSubDone(self)
        self._progress.show()
        self._fetcher.getFeedback().error(self, "file not found")

    def getStatus(self):
        return self._status

    def setStatus(self, status):
        self._status = status

    def getURL(self):
        return self._url

    def getFetcher(self):
        return self._fetcher

    def getProgress(self):
        return self._progress

    def setProgress(self, prog):
        self._progress = prog

    def getFileName(self):
        return self._filename

    def setFileName(self, filename):
        self._filename = filename

    def get(self):
        self._status = RUNNING
        prog = self._progress
        prog.setSubTopic(self, os.path.basename(self._url))
        prog.setSub(self, 0, 1)
        feedback = self._fetcher.getFeedback()
        feedback.starting(self)
        prog.show()
        self.acquire()
        if self._status != FAILED:
            prog.add(1)
        prog.setSubDone(self)
        prog.show()
        feedback.finished(self)
        return self._filename

    def getCached(self):
        fetcher = self._fetcher
        filename = fetcher.getCachePath(self._url)
        if not os.path.isfile(filename):
            filename = None
        elif not self.checkCached(filename):
            os.unlink(filename)
            filename = None
        if filename:
            self._status = SUCCEEDED
        else:
            self._status = FAILED
        self._filename = filename
        return filename

    def checkCached(self, filename):
        return True

    def acquire(self):
        pass


class FileHandler(Handler):

    def getCached(self):
        filename = self._url[7:]
        if os.path.isfile(filename):
            self._status = SUCCEEDED
        else:
            self._status = FAILED
            filename = None
        self._filename = filename
        return filename

    def acquire(self):
        self._progress.setSub(0, 1)
        self.getCached()
        if self._status == FAILED:
            self.error("file not found")

Fetcher.setHandler("file", FileHandler)

class URLLIB2Handler(Handler):

    BLOCKSIZE = 8192

    _openerinstalled = False
    _usecachedftp = False

    def __init__(self, *args):
        Handler.__init__(self, *args)
        if not URLLIB2Handler._openerinstalled:
            import urllib2
            URLLIB2Handler._openerinstalled = True
            if self._usecachedftp:
                opener = urllib2.build_opener(urllib2.CacheFTPHandler)
                urllib2.install_opener(opener)

    def acquire(self):
        import urllib2
        try:
            remote = urllib2.urlopen(self._url)
            info = remote.info()
            localpath = self._fetcher.getCachePath(self._url)
            try:
                local = open(localpath, "w")
            except (IOError, OSError), e:
                raise IOError, "%s: %s" % (localpath, e)
            prog = self._progress
            current = 0
            total = int(info["content-length"])
            bs = self.BLOCKSIZE
            data = remote.read(bs)
            while data:
                local.write(data)
                current += len(data)
                if current != total:
                    prog.setSub(self, current, total)
                    prog.show()
                data = remote.read(bs)
            local.close()
            remote.close()
        except (IOError, OSError), e:
            self.error(str(e))
            self._status = FAILED
        else:
            self._status = SUCCEEDED
            self._filename = localpath

Fetcher.setHandler("ftp", URLLIB2Handler)
Fetcher.setHandler("http", URLLIB2Handler)
Fetcher.setHandler("https", URLLIB2Handler)
Fetcher.setHandler("gopher", URLLIB2Handler)

class PyCurlHandler(Handler):

    def __init__(self, fetcher, url, progress):
        import pycurl
        Handler.__init__(self, fetcher, url, progress)
        self._handler = pycurl.Curl()
        self._handler.setopt(pycurl.URL, url)
        self._handler.setopt(pycurl.NOPROGRESS, 0)
        self._handler.setopt(pycurl.PROGRESSFUNCTION, self.progress)

    def progress(self, downtotal, downcurrent, uptotal, upcurrent):
        self._progress.setSub(self, downcurrent, downtotal)

    def acquire(self):
        import pycurl
        try:
            localpath = self._fetcher.getCachePath(self._url)
            try:
                local = open(localpath, "w")
            except (IOError, OSError), e:
                raise IOError, "%s: %s" % (localpath, e)
            self._handler.setopt(pycurl.WRITEDATA, local)
            self._handler.perform()
            local.close()
        except (IOError, OSError), e:
            self.error(str(e))
            self._status = FAILED
        else:
            self._status = SUCCEEDED
            self._filename = localpath

Fetcher.setHandler("ftp", PyCurlHandler)

# vim:ts=4:sw=4

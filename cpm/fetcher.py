from cpm.const import OPTIONAL, ALWAYS, NEVER
from cpm.progress import Progress
from cpm import *
import tempfile
import urllib
import string
import thread
import time
import os


class Fetcher(object):

    _registry = {}

    def __init__(self):
        self._progress = Progress()
        self._localdir = tempfile.gettempdir()
        self._mangle = False
        self._caching = OPTIONAL
        self.reset()

    def reset(self):
        self._handlers = {}
        self._validators = {}
        self._failed = {}
        self._succeeded = {}

    def getProgress(self):
        return self._progress

    def setProgress(self, prog):
        self._progress = prog

    def getFailedSet(self):
        return self._failed

    def getFailed(self, url):
        return self._failed.get(url)
    
    def setFailed(self, url, msg=None):
        if not msg:
            msg = "unknown reason"
        self._failed[url] = msg

    def getSucceededSet(self):
        return self._succeeded

    def getSucceeded(self, url):
        return self._succeeded.get(url)

    def setSucceeded(self, url, localpath):
        self._succeeded[url] = localpath

    def getCaching(self):
        return self._caching

    def setCaching(self, value):
        self._caching = value

    def setValidator(self, url, validator):
        self._validators[url] = validator

    def getValidator(self, url):
        return self._validators.get(url)

    def validate(self, url, localpath):
        if not os.path.isfile(localpath):
            return False, "local file not found"
        validator = self._validators.get(url)
        if validator:
            res = validator(url, localpath)
            if type(res) is not tuple:
                return res, None
            else:
                return res
        return True, None

    def setLocalDir(self, localdir, mangle=False):
        self._localdir = localdir
        self._mangle = mangle

    def getLocalDir(self):
        return self._localdir

    def getLocalPath(self, url):
        if self._mangle:
            filename = url.replace("/", "_")
        else:
            scheme, selector = urllib.splittype(url)
            host, path = urllib.splithost(selector)
            path, query = urllib.splitquery(path)
            path = urllib.unquote(path)
            filename = os.path.basename(path)
        return os.path.join(self._localdir, filename)

    def enqueue(self, url):
        handler = self.getHandlerInstance(url)
        handler.enqueue(url)

    def run(self, what):
        handlers = self._handlers.values()
        prog = self._progress
        prog.reset()
        prog.setTopic("Fetching %s..." % what)
        total = 0
        for handler in handlers:
            total += len(handler.getQueue())
        prog.set(0, total)
        if self._caching is not NEVER:
            for handler in handlers:
                for url in handler.getQueue()[:]:
                    localpath = self.getLocalPath(url)
                    valid, reason = self.validate(url, localpath)
                    if valid:
                        handler.dequeue(url)
                        self.setSucceeded(url, localpath)
                        prog.add(1)
                    elif self._caching is ALWAYS:
                        handler.dequeue(url)
                        self.setFailed(url, reason)
        if self._caching is ALWAYS:
            return
        for handler in handlers:
            handler.start()
        active = handlers[:]
        while active:
            for handler in active[:]:
                if not handler.tick():
                    active.remove(handler)
            time.sleep(0.1)
        for handler in handlers:
            handler.stop()

    def setHandler(self, scheme, klass):
        self._registry[scheme] = klass
    setHandler = classmethod(setHandler)

    def getHandler(self, scheme, klass):
        return self._registry.get(scheme)
    getHandler = classmethod(getHandler)

    def getHandlerInstance(self, url):
        scheme, selector = urllib.splittype(url)
        handler = self._handlers.get(scheme)
        if not handler:
            klass = self._registry.get(scheme)
            if not klass:
                raise Error, "unsupported scheme: %s" % scheme
            handler = klass(self, self._progress)
            self._handlers[scheme] = handler
        return handler

class URL(object):
    def __init__(self, url=None):
        if url:
            self.set(url)
        else:
            self.reset()

    def reset(self):
        self.original = ""
        self.scheme = ""
        self.user = ""
        self.passwd = ""
        self.host = ""
        self.port = None
        self.path = ""
        self.query = ""

    def set(self, url):
        self.scheme, rest = urllib.splittype(url)
        if self.scheme == "file":
            self.reset()
            self.original = url
            self.path = os.path.normpath(rest)
            return
        self.original = url
        host, rest = urllib.splithost(rest)
        user, host = urllib.splituser(host)
        if user:
            self.user, self.passwd = urllib.splitpasswd(user)
        else:
            self.user = ""
            self.passwd = ""
        self.host, self.port = urllib.splitport(host)
        self.path, self.query = urllib.splitquery(rest)

        self.user = urllib.unquote(self.user)
        self.passwd = urllib.unquote(self.passwd)
        self.path = urllib.unquote(self.path)

    def __str__(self):
        if self.scheme == "file":
            return "file://"+urllib.quote(self.path)
        url = self.scheme+"://"
        if self.user:
            url += urllib.quote(self.user)
            if self.passwd:
                url += ":"
                url += urllib.quote(self.passwd)
            url += "@"
        url += self.host
        if self.port:
            url += ":%d" % self.port
        if self.path:
            url += urllib.quote(self.path)
        else:
            url += "/"
        if self.query:
            url += "?"
            url += self.query
        return url

class Handler(object):
    def __init__(self, fetcher, progress):
        self._fetcher = fetcher
        self._progress = progress
        self._queue = []

    def getQueue(self):
        return self._queue

    def enqueue(self, url):
        if url not in self._queue:
            self._queue.append(url)

    def dequeue(self, url):
        self._queue.remove(url)

    def start(self):
        pass

    def stop(self):
        pass

    def tick(self):
        return False

class FileHandler(Handler):

    def start(self):
        for url in self._queue:
            urlobj = URL(url)
            if os.path.isfile(urlobj.path):
                self._fetcher.setSucceeded(url, urlobj.path)
            else:
                self._fetcher.setFailed(url, "file not found")
        self._queue = []

Fetcher.setHandler("file", FileHandler)

class FTPHandler(Handler):

    MAXACTIVE = 5
    MAXINACTIVE = 10
    MAXPERHOST = 2

    def __init__(self, *args):
        Handler.__init__(self, *args)
        self._active = {}   # ftp -> host
        self._inactive = {} # ftp -> (user, host, port)
        self._lock = thread.allocate_lock()

    def tick(self):
        import ftplib
        self._lock.acquire()
        if self._queue:
            if len(self._active) < self.MAXACTIVE:
                for i in range(len(self._queue)-1,-1,-1):
                    url = self._queue[i]
                    urlobj = URL(url)
                    hostactive = [x for x in self._active
                                     if self._active[x] == urlobj.host]
                    if len(hostactive) < self.MAXPERHOST:
                        del self._queue[i]
                        userhost = (urlobj.user, urlobj.host, urlobj.port)
                        for ftp in self._inactive:
                            if self._inactive[ftp] == userhost:
                                del self._inactive[ftp]
                                self._active[ftp] = urlobj.host
                                thread.start_new_thread(self.fetch,
                                                        (ftp, urlobj))
                                break
                        else:
                            if len(self._inactive) > self.MAXINACTIVE:
                                del self._inactive[ftp]
                            ftp = ftplib.FTP()
                            self._active[ftp] = urlobj.host
                            thread.start_new_thread(self.connect,
                                                    (ftp, urlobj))
        self._lock.release()
        return bool(self._queue or self._active)

    def connect(self, ftp, urlobj):
        url = urlobj.original
        prog = self._progress
        # XXX Ask topic for the interface?
        prog.setSubTopic(url, os.path.basename(url))
        prog.setSub(url, 0, 1, 1)
        prog.show()
        import socket
        try:
            ftp.connect(urlobj.host, urlobj.port)
            ftp.login(urlobj.user, urlobj.passwd)
        except socket.error, e:
            prog.setSubDone(url)
            prog.show()
            self.setFailed(url, str(e))
        else:
            self.fetch(ftp, urlobj)

    def fetch(self, ftp, urlobj):
        import socket, ftplib
        url = urlobj.original
        prog = self._progress
        # XXX Ask topic for the interface?
        prog.setSubTopic(url, os.path.basename(url))
        prog.setSub(url, 0, 1, 1)
        prog.show()
        try:
            ftp.cwd(os.path.dirname(urlobj.path))
            filename = os.path.basename(urlobj.path)
            ftp.nlst(filename)
            try:
                total = ftp.size(filename)
            except ftplib.Error:
                total = None
            localpath = self._fetcher.getLocalPath(url)
            try:
                local = open(localpath, "w")
            except (IOError, OSError), e:
                raise IOError, "%s: %s" % (localpath, e)
            urlobj.current = 0
            def write(data):
                local.write(data)
                urlobj.current += len(data)
                if total:
                    prog.setSub(url, urlobj.current, total, 1)
                    prog.show()
            ftp.retrbinary("RETR "+filename, write, 8192)
            if not total:
                prog.setSubDone(url)
                prog.show()
            local.close()
        except socket.error:
            prog.setSub(url, 0, 1, 1)
            self._lock.acquire()
            self._queue.append(url)
            del self._active[ftp]
            self._lock.release()
            return
        except ftplib.Error, e:
            prog.setSubDone(url)
            self._fetcher.setFailed(url, str(e))
        else:
            self._fetcher.setSucceeded(url, localpath)

        self._lock.acquire()
        self._inactive[ftp] = (urlobj.user, urlobj.host, urlobj.port)
        del self._active[ftp]
        self._lock.release()

Fetcher.setHandler("ftp", FTPHandler)

class URLLIB2Handler(Handler):

    MAXACTIVE = 1 # urllib2 is not thread safe
    USECACHEDFTP = True

    _openerinstalled = False

    def __init__(self, *args):
        Handler.__init__(self, *args)
        if not URLLIB2Handler._openerinstalled:
            import urllib2
            URLLIB2Handler._openerinstalled = True
            if self.USECACHEDFTP:
                opener = urllib2.build_opener(urllib2.CacheFTPHandler)
                urllib2.install_opener(opener)
        self._active = 0
        self._lock = thread.allocate_lock()

    def start(self):
        self._queue.sort()

    def tick(self):
        self._lock.acquire()
        if self._queue:
            while self._active < self.MAXACTIVE:
                self._active += 1
                thread.start_new_thread(self.fetch, ())
        self._lock.release()
        return bool(self._queue or self._active)

    def fetch(self):
        prog = self._progress
        import urllib2
        while True:

            self._lock.acquire()
            if not self._queue:
                self._lock.release()
                break
            url = self._queue.pop()
            self._lock.release()

            try:
                # XXX Ask topic for the interface?
                prog.setSubTopic(url, os.path.basename(url))
                prog.setSub(url, 0, 1, 1)
                prog.show()
                remote = urllib2.urlopen(url)
                info = remote.info()
                localpath = self._fetcher.getLocalPath(url)
                try:
                    local = open(localpath, "w")
                except (IOError, OSError), e:
                    raise IOError, "%s: %s" % (localpath, e)
                prog = self._progress
                current = 0
                if "content-length" in info:
                    total = int(info["content-length"])
                else:
                    total = None
                data = remote.read(8192)
                while data:
                    local.write(data)
                    current += len(data)
                    if total:
                        prog.setSub(url, current, total, 1)
                        prog.show()
                    data = remote.read(bs)
                if not total:
                    prog.setSubDone(url)
                    prog.show()
                local.close()
                remote.close()
            except (IOError, OSError), e:
                prog.setSubDone(url)
                self._fetcher.setFailed(url, str(e))
            else:
                self._fetcher.setSucceeded(url, localpath)

        self._lock.acquire()
        self._active -= 1
        self._lock.release()

Fetcher.setHandler("http", URLLIB2Handler)
Fetcher.setHandler("https", URLLIB2Handler)
Fetcher.setHandler("gopher", URLLIB2Handler)

class PyCurlHandler(Handler):

    MAXHANDLERS = 10

    def __init__(self, fetcher, url, progress):
        import pycurl
        Handler.__init__(self, fetcher, url, progress)
        self._multi = pycurl.CurlMulti()
        self._handler = pycurl.Curl()
        self._handler.setopt(pycurl.URL, url)
        self._handler.setopt(pycurl.NOPROGRESS, 0)
        self._handler.setopt(pycurl.PROGRESSFUNCTION, self.progress)

    def progress(self, downtotal, downcurrent, uptotal, upcurrent):
        self._progress.setSub(self, downcurrent, downtotal)

    def acquire(self):
        import pycurl
        try:
            localpath = self._fetcher.getLocalPath(self._url)
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

#Fetcher.setHandler("ftp", PyCurlHandler)

# vim:ts=4:sw=4

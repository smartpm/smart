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
        self._info = {}

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

    def setInfo(self, url, size=None, md5=None, sha=None):
        if md5: md5 = md5.lower()
        if sha: sha = sha.lower()
        self._info[url] = {"size": size, "md5": md5, "sha": sha}

    def getInfo(self, url, kind, default=None):
        return self._info.get(url, {}).get(kind, default)

    def getSize(self):
        total = 0
        for handler in self._handlers.values():
            for url in handler.getQueue():
                total += self.getInfo(url, "size", 0)
        return total

    def getCaching(self):
        return self._caching

    def setCaching(self, value):
        self._caching = value

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

    def enqueue(self, url, **info):
        self.setInfo(url, **info)
        handler = self.getHandlerInstance(url)
        handler.enqueue(url)

    def runLocal(self):
        for handler in self._handlers.values():
            handler.runLocal()

    def run(self, what):
        handlers = self._handlers.values()
        self.runLocal()
        if self._caching is ALWAYS:
            for handler in handlers:
                for url in handler.getQueue()[:]:
                    handler.dequeue(url)
                    self.setFailed(url, "local file not found")
            return
        prog = self._progress
        prog.reset()
        prog.setTopic("Fetching %s..." % what)
        total = 0
        for handler in handlers:
            total += len(handler.getQueue())
        prog.set(0, total)
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

    def validate(self, url, localpath, withreason=False):
        try:
            if not os.path.isfile(localpath):
                raise Error, "file not found"
            size = self.getInfo(url, "size")
            if size:
                lsize = os.path.getsize(localpath)
                if lsize != size:
                    raise Error, "invalid size (expected %d, got %d)" % \
                                 (size, lsize)
            filemd5 = self.getInfo(url, "md5")
            if filemd5:
                import md5
                digest = md5.md5()
                file = open(localpath)
                data = file.read(8192)
                while data:
                    digest.update(data)
                    data = file.read(8192)
                lfilemd5 = digest.hexdigest()
                if lfilemd5 != filemd5:
                    raise Error, "invalid MD5 (expected %s, got %s)" % \
                                 (filemd5, lfilemd5)
            else:
                filesha = self.getInfo(url, "sha")
                if filesha:
                    import sha
                    digest = sha.sha()
                    file = open(localpath)
                    data = file.read(8192)
                    while data:
                        digest.update(data)
                        data = file.read(8192)
                    lfilesha = digest.hexdigest()
                    if lfilesha != filesha:
                        raise Error, "invalid SHA (expected %s, got %s)" % \
                                     (filesha, lfilesha)
        except Error, reason:
            if withreason:
                return False, reason
            return False
        else:
            if withreason:
                return True, None
            return True

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
        self._queue.sort()

    def stop(self):
        pass

    def tick(self):
        return False

    def runLocal(self):
        fetcher = self._fetcher
        if fetcher.getCaching() is not NEVER:
            for i in range(len(self._queue)-1,-1,-1):
                url = self._queue[i]
                localpath = fetcher.getLocalPath(url)
                if fetcher.validate(url, localpath):
                    del self._queue[i]
                    fetcher.setSucceeded(url, localpath)

class FileHandler(Handler):

    def runLocal(self):
        fetcher = self._fetcher
        for url in self._queue:
            urlobj = URL(url)
            valid, reason = fetcher.validate(url, urlobj.path, True)
            if valid:
                fetcher.setSucceeded(url, urlobj.path)
            else:
                fetcher.setFailed(url, reason)
        del self._queue[:]

Fetcher.setHandler("file", FileHandler)

class FTPHandler(Handler):

    MAXACTIVE = 5
    MAXINACTIVE = 5
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
        prog.setSubTopic(url, os.path.basename(urlobj.path))
        prog.setSub(url, 0, 1, 1)
        prog.show()
        import socket
        try:
            ftp.connect(urlobj.host, urlobj.port)
            ftp.login(urlobj.user, urlobj.passwd)
        except socket.error, e:
            self._fetcher.setFailed(url, str(e[1]))
            prog.setSubDone(url)
            prog.show()
            self._lock.acquire()
            del self._active[ftp]
            self._lock.release()
        else:
            self.fetch(ftp, urlobj)

    def fetch(self, ftp, urlobj):
        import socket, ftplib

        fetcher = self._fetcher
        url = urlobj.original
        prog = self._progress

        prog.setSubTopic(url, os.path.basename(urlobj.path))
        prog.setSub(url, 0, 1, 1)
        prog.show()

        succeeded = False

        try:
            ftp.cwd(os.path.dirname(urlobj.path))
            filename = os.path.basename(urlobj.path)
            localpath = fetcher.getLocalPath(url)

            mtime = None
            total = None

            # Check if the file exists at all.
            ftp.nlst(filename)

            try:
                resp = ftp.sendcmd("MDTM "+filename)
                if resp[:3] == "213":
                    mtimes = resp[3:].strip()
                    mtime = time.mktime(time.strptime(mtimes, "%Y%m%d%H%M%S"))
            except (ftplib.Error, ValueError):
                pass

            try:
                total = ftp.size(filename)
            except ftplib.Error:
                pass
            else:
                size = fetcher.getInfo(url, "size")
                if size and size != total:
                    raise Error, "server reports invalid size"

            if (not mtime or not os.path.isfile(localpath) or
                mtime != os.path.getmtime(localpath) or
                not fetcher.validate(url, localpath)):

                localpathpart = localpath+".part"
                if (os.path.isfile(localpathpart) and
                    (not total or os.path.getsize(localpathpart) < total)):
                    rest = os.path.getsize(localpathpart)
                    openmode = "a"
                    urlobj.current = rest
                else:
                    rest = None
                    openmode = "w"
                    urlobj.current = 0

                try:
                    local = open(localpathpart, openmode)
                except (IOError, OSError), e:
                    raise Error, "%s: %s" % (localpathpart, e)

                def write(data):
                    local.write(data)
                    urlobj.current += len(data)
                    if total:
                        prog.setSub(url, urlobj.current, total, 1)
                        prog.show()

                try:
                    ftp.retrbinary("RETR "+filename, write, 8192, rest)
                finally:
                    local.close()

                if mtime:
                    os.utime(localpathpart, (mtime, mtime))

                os.rename(localpathpart, localpath)

                valid, reason = fetcher.validate(url, localpath, True)
                if not valid:
                    if openmode == "a":
                        # Try again, from the very start.
                        prog.setSubDone(url)
                        prog.show()
                        prog.resetSub(url)
                        self._lock.acquire()
                        self._queue.append(url)    
                        self._lock.release()
                    else:
                        raise Error, reason
                else:
                    succeeded = True
            else:
                succeeded = True

        except socket.error:
            # Put it back on the queue, and kill this ftp object.
            self._lock.acquire()
            self._queue.append(url)
            del self._active[ftp]
            self._lock.release()
            return

        except (Error, IOError, OSError, ftplib.Error), e:
            fetcher.setFailed(url, str(e))
            prog.setSubDone(url)
            prog.show()

        if succeeded:
            fetcher.setSucceeded(url, localpath)
            prog.setSubDone(url)
            prog.show()

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

    def tick(self):
        self._lock.acquire()
        if self._queue:
            while self._active < self.MAXACTIVE:
                self._active += 1
                thread.start_new_thread(self.fetch, ())
        self._lock.release()
        return bool(self._queue or self._active)

    def fetch(self):
        import urllib2, rfc822
        
        fetcher = self._fetcher
        prog = self._progress

        while True:

            self._lock.acquire()
            if not self._queue:
                self._lock.release()
                break
            url = self._queue.pop()
            self._lock.release()

            prog.setSubTopic(url, os.path.basename(URL(url).path))
            prog.setSub(url, 0, 1, 1)
            prog.show()

            succeeded = False

            try:

                localpath = fetcher.getLocalPath(url)
                current = 0
                total = None

                size = fetcher.getInfo(url, "size")

                request = urllib2.Request(url)
                if (os.path.isfile(localpath) and
                    fetcher.validate(url, localpath)):
                    mtime = os.path.getmtime(localpath)
                    request.add_header("if-modified-since",
                                       rfc822.formatdate(mtime))

                localpathpart = localpath+".part"
                if os.path.isfile(localpathpart):
                    partsize = os.path.getsize(localpathpart)
                    if not size or partsize < size:
                        request.add_header("range", "bytes=%d-" % partsize)

                try:
                    remote = urllib2.urlopen(request)
                except urllib2.HTTPError, e:
                    if e.code == 416: # Range not satisfiable
                        del request.headers["Range"]
                        remote = urllib2.urlopen(request)
                    else:
                        raise

                info = remote.info()

                if "content-length" in info:
                    total = int(info["content-length"])

                if "content-range" in info:
                    openmode = "a"
                    current = partsize
                    total += partsize
                else:
                    openmode = "w"

                if size and total and size != total:
                    raise Error, "server reports invalid size"

                try:
                    local = open(localpathpart, openmode)
                except (IOError, OSError), e:
                    raise IOError, "%s: %s" % (localpathpart, e)

                try:
                    data = remote.read(8192)
                    while data:
                        local.write(data)
                        current += len(data)
                        if total:
                            prog.setSub(url, current, total, 1)
                            prog.show()
                        data = remote.read(8192)
                finally:
                    local.close()
                    remote.close()

                os.rename(localpathpart, localpath)

                valid, reason = fetcher.validate(url, localpath, True)
                if not valid:
                    if openmode == "a":
                        # Try again, from the very start.
                        prog.setSubDone(url)
                        prog.show()
                        prog.resetSub(url)
                        self._lock.acquire()
                        self._queue.append(url)
                        self._lock.release()
                    else:
                        raise Error, reason
                else:
                    succeeded = True

                    if "last-modified" in info:
                        mtimes = info["last-modified"]
                        mtimet = rfc822.parsedate(mtimes)
                        if mtimet:
                            mtime = time.mktime(mtimet)
                            os.utime(localpath, (mtime, mtime))

            except urllib2.HTTPError, e:
                if e.code == 304: # Not modified
                    succeeded = True
                else:
                    fetcher.setFailed(url, str(e))
                    prog.setSubDone(url)
                    prog.show()

            except (IOError, OSError, Error), e:
                fetcher.setFailed(url, str(e))
                prog.setSubDone(url)
                prog.show()

            if succeeded:
                fetcher.setSucceeded(url, localpath)
                prog.setSubDone(url)
                prog.show()

        self._lock.acquire()
        self._active -= 1
        self._lock.release()

#Fetcher.setHandler("ftp", URLLIB2Handler)
Fetcher.setHandler("http", URLLIB2Handler)
Fetcher.setHandler("https", URLLIB2Handler)
Fetcher.setHandler("gopher", URLLIB2Handler)

class PyCurlHandler(Handler):

    MAXACTIVE = 5
    MAXINACTIVE = 5
    MAXPERHOST = 2

    def __init__(self, *args):
        import pycurl
        Handler.__init__(self, *args)
        self._active = {}   # handle -> (scheme, host)
        self._inactive = {} # handle -> (user, host, port)
        self._multi = pycurl.CurlMulti()
        self._lock = thread.allocate_lock()

    def start(self):
        self._queue.sort()
        thread.start_new_thread(self.perform, ())

    def tick(self):
        import pycurl

        fetcher = self._fetcher
        prog = self._progress
        multi = self._multi

        num = 1
        while num != 0:

            self._lock.acquire()
            num, succeeded, failed = multi.info_read()
            self._lock.release()

            for handle in succeeded:

                urlobj = handle.urlobj
                local = handle.local
                localpath = handle.localpath

                local.close()

                prog.setSubDone(urlobj.original)
                prog.show()

                self._lock.acquire()
                multi.remove_handle(handle)
                self._lock.release()

                if handle.getinfo(pycurl.SIZE_DOWNLOAD) == 0:
                    # Not modified
                    os.unlink(localpath+".part")
                else:
                    if os.path.isfile(localpath):
                        os.unlink(localpath)
                    os.rename(localpath+".part", localpath)
                    mtime = handle.getinfo(pycurl.INFO_FILETIME)
                    if mtime != -1:
                        os.utime(localpath, (mtime, mtime))

                del self._active[handle]
                userhost = (urlobj.user, urlobj.host, urlobj.port)
                self._inactive[handle] = userhost

                valid, reason = fetcher.validate(urlobj.original,
                                                 localpath, True)
                if valid:
                    fetcher.setSucceeded(urlobj.original, localpath)
                elif handle.resuming:
                    self._queue.append(urlobj.original)
                else:
                    fetcher.setFailed(urlobj.original, reason)

            for handle, errno, errmsg in failed:

                urlobj = handle.urlobj
                local = handle.local
                localpath = handle.localpath

                local.close()

                prog.setSubDone(urlobj.original)
                prog.show()

                self._lock.acquire()
                multi.remove_handle(handle)
                self._lock.release()

                del self._active[handle]
                userhost = (urlobj.user, urlobj.host, urlobj.port)
                self._inactive[handle] = userhost

                if handle.resuming and "byte ranges" in errmsg:
                    os.unlink(localpath+".part")
                    prog.resetSub(urlobj.original)
                    self._queue.append(urlobj.original)
                else:
                    fetcher.setFailed(urlobj.original, errmsg)


        if self._queue:
            if len(self._active) < self.MAXACTIVE:
                for i in range(len(self._queue)-1,-1,-1):
                    url = self._queue[i]
                    urlobj = URL(url)
                    schemehost = (urlobj.scheme, urlobj.host)
                    hostactive = [x for x in self._active
                                     if self._active[x] == schemehost]
                    if len(hostactive) < self.MAXPERHOST:
                        del self._queue[i]

                        userhost = (urlobj.user, urlobj.host, urlobj.port)
                        for handle in self._inactive:
                            if self._inactive[handle] == userhost:
                                del self._inactive[handle]
                                self._active[handle] = schemehost
                                break
                        else:
                            if len(self._inactive) > self.MAXINACTIVE:
                                del self._inactive[handle]
                            handle = pycurl.Curl()
                            self._active[handle] = schemehost

                        localpath = fetcher.getLocalPath(url)
                        localpathpart = localpath+".part"

                        size = fetcher.getInfo(url, "size")

                        if os.path.isfile(localpathpart):
                            partsize = os.path.getsize(localpathpart)
                            if size and partsize >= size:
                                partsize = 0
                        else:
                            partsize = 0
                        if partsize:
                            openmode = "a"
                            handle.resuming = True
                            handle.setopt(pycurl.RESUME_FROM_LARGE,
                                          long(partsize))
                        else:
                            openmode = "w"
                            handle.resuming = False
                            handle.setopt(pycurl.RESUME_FROM_LARGE, 0L)

                        try:
                            local = open(localpathpart, openmode)
                        except (IOError, OSError), e:
                            fetcher.setFailed(url, "%s: %s" %
                                              (localpathpart, e))

                        handle.urlobj = urlobj
                        handle.local = local
                        handle.localpath = localpath

                        prog.setSubTopic(url, os.path.basename(urlobj.path))
                        prog.setSub(url, 0, 1, 1)
                        prog.show()

                        def progress(downtotal, downcurrent,
                                     uptotal, upcurrent, url=url,
                                     size=size, partsize=partsize):
                            if not downtotal:
                                if size and downcurrent:
                                    prog.setSub(url, partsize+downcurrent,
                                                size, 1)
                                else:
                                    prog.setSub(url, 0, 1, 1)
                            else:
                                prog.setSub(url, partsize+downcurrent,
                                            partsize+downtotal, 1)
                            prog.show()

                        handle.setopt(pycurl.URL, url)
                        handle.setopt(pycurl.OPT_FILETIME, 1)
                        handle.setopt(pycurl.NOPROGRESS, 0)
                        handle.setopt(pycurl.PROGRESSFUNCTION, progress)
                        handle.setopt(pycurl.WRITEDATA, local)

                        if fetcher.validate(url, localpath):
                            handle.setopt(pycurl.TIMECONDITION,
                                          pycurl.TIMECOND_IFMODSINCE)
                            mtime = os.path.getmtime(localpath)
                            if urlobj.scheme == "ftp":
                                mtime += 1 # libcurl handles ftp mtime wrongly
                            handle.setopt(pycurl.TIMEVALUE, mtime)

                        self._lock.acquire()
                        multi.add_handle(handle)
                        self._lock.release()

        return bool(self._queue or self._active)

    def perform(self):
        import pycurl
        multi = self._multi
        mp = pycurl.E_CALL_MULTI_PERFORM
        while self._queue or self._active:
            self._lock.acquire()
            res = mp
            while res == mp:
                res, num = multi.perform()
            self._lock.release()
            time.sleep(0.2)

try:
    import pycurl
except ImportError:
    pass
else:
    schemes = pycurl.version_info()[-1]
    for scheme in schemes:
        if scheme != "file":
            Fetcher.setHandler(scheme, PyCurlHandler)

# vim:ts=4:sw=4:et

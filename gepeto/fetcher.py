#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Gepeto.
#
# Gepeto is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gepeto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gepeto; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from gepeto.uncompress import Uncompressor
from gepeto.mirror import MirrorSystem
from media import MediaSet
from gepeto.const import *
from gepeto import *
import tempfile
import urllib
import string
import thread
import time
import os
import re

LOCALSCHEMES = ["file", "localmedia"]

class Fetcher(object):

    _registry = {}

    MAXRETRIES = 3

    def __init__(self):
        self._uncompressor = Uncompressor()
        self._mediaset = MediaSet()
        self._uncompressing = 0
        self._localdir = tempfile.gettempdir()
        self._mirror = MirrorSystem()
        self._mangle = False
        self._caching = OPTIONAL
        self._items = {}
        self._handlers = {}
        self._forcecopy = False
        self._localpathprefix = None

    def reset(self):
        self._items.clear()
        self._uncompressing = 0

    def getItem(self, url):
        return self._items.get(url)

    def getItems(self):
        return self._items.values()

    def getSucceededSet(self):
        set = {}
        for item in self._items.values():
            if item.getStatus() == SUCCEEDED:
                set[item.getOriginalURL()] = item.getTargetPath()
        return set

    def getFailedSet(self):
        set = {}
        for item in self._items.values():
            if item.getStatus() == FAILED:
                set[item.getOriginalURL()] = item.getFailedReason()
        return set

    def getUncompressor(self):
        return self._uncompressor

    def getMediaSet(self):
        return self._mediaset

    def getCaching(self):
        return self._caching

    def setCaching(self, value):
        self._caching = value

    def setLocalDir(self, localdir, mangle=False):
        self._localdir = localdir
        self._mangle = mangle

    def getLocalDir(self):
        return self._localdir

    def setLocalPathPrefix(self, prefix):
        self._localpathprefix = prefix

    def getLocalPathPrefix(self):
        return self._localpathprefix

    def getLocalPath(self, item):
        assert isinstance(item, FetchItem)
        url = item.getOriginalURL()
        if self._mangle:
            filename = url.replace("/", "_")
        else:
            scheme, selector = urllib.splittype(url)
            host, path = urllib.splithost(selector)
            path, query = urllib.splitquery(path)
            path = urllib.unquote(path)
            filename = os.path.basename(path)
        if self._localpathprefix:
            filename = self._localpathprefix+filename
        return os.path.join(self._localdir, filename)

    def setForceCopy(self, value):
        self._forcecopy = value

    def getForceCopy(self):
        return self._forcecopy

    def enqueue(self, url, **info):
        if url in self._items:
            raise Error, "%s is already in the queue" % url
        mirror = self._mirror.get(url)
        item = FetchItem(self, url, mirror)
        self._items[url] = item
        if info:
            item.setInfo(**info)
        handler = self.getHandlerInstance(item)
        handler.enqueue(item)
        return item

    def runLocal(self):
        for handler in self._handlers.values():
            handler.runLocal()

    def run(self, what=None, progress=None):
        handlers = self._handlers.values()
        total = len(self._items)
        self.runLocal()
        local = len([x for x in self._items.values()
                     if x.getStatus() == SUCCEEDED])
        if local == total or self._caching is ALWAYS:
            if progress:
                progress.add(total)
            return
        if progress:
            prog = progress
            prog.add(local)
            if what:
                prog.setTopic("Fetching %s..." % what)
            prog.show()
        else:
            prog = iface.getProgress(self, True)
            prog.start()
            prog.set(local, total)
            if what:
                topic = "Fetching %s..." % what
            else:
                topic = "Fetching information..."
            prog.setTopic(topic)
            prog.show()
        for handler in handlers:
            handler.start()
        active = handlers[:]
        uncomp = self._uncompressor
        uncompchecked = {}
        while active or self._uncompressing:
            for handler in active[:]:
                if not handler.tick():
                    active.remove(handler)
            for url in self._items:
                item = self._items[url]
                if item.getStatus() == FAILED:
                    if (item.getRetries() < self.MAXRETRIES and
                        item.setNextURL()):
                        item.reset()
                        handler = self.getHandlerInstance(item)
                        handler.enqueue(item)
                        if handler not in active:
                            active.append(handler)
                    continue
                elif (item.getStatus() != SUCCEEDED or
                      not item.getInfo("uncomp")):
                    continue
                localpath = item.getTargetPath()
                if localpath in uncompchecked:
                    continue
                uncompchecked[localpath] = True
                uncomphandler = uncomp.getHandler(localpath)
                if not uncomphandler:
                    continue
                uncomppath = uncomphandler.getTargetPath(localpath)
                if (not self.hasStrongValidate(item, uncomp=True) or
                    not self.validate(item, uncomppath, uncomp=True)):
                    self._uncompressing += 1
                    thread.start_new_thread(self._uncompress,
                                            (item, localpath, uncomphandler))
                else:
                    item.setSucceeded(uncomppath)
            prog.show()
            time.sleep(0.1)
        for handler in handlers:
            handler.stop()
        if not progress:
            prog.stop()

    def _uncompress(self, item, localpath, uncomphandler):
        try:
            uncomphandler.uncompress(localpath)
        except Error, e:
            item.setFailed(str(e))
        else:
            uncomppath = uncomphandler.getTargetPath(localpath)
            valid, reason = self.validate(item, uncomppath,
                                          withreason=True, uncomp=True)
            if not valid:
                item.setFailed(reason)
            else:
                item.setSucceeded(uncomppath)
        self._uncompressing -= 1

    def setHandler(self, scheme, klass):
        self._registry[scheme] = klass
    setHandler = classmethod(setHandler)

    def getHandler(self, scheme, klass):
        return self._registry.get(scheme)
    getHandler = classmethod(getHandler)

    def getHandlerInstance(self, item):
        scheme = item.getURL().scheme
        handler = self._handlers.get(scheme)
        if not handler:
            klass = self._registry.get(scheme)
            if not klass:
                raise Error, "Unsupported scheme: %s" % scheme
            handler = klass(self)
            self._handlers[scheme] = handler
        return handler

    def hasStrongValidate(self, item, uncomp=False):
        if uncomp:
            prefix = "uncomp_"
        else:
            prefix = ""
        return bool(item.getInfo(prefix+"md5") or item.getInfo(prefix+"sha"))

    def validate(self, item, localpath, withreason=False, uncomp=False):
        try:
            if not os.path.isfile(localpath):
                raise Error, "File not found"

            if uncomp:
                uncompprefix = "uncomp_"
            else:
                uncompprefix = ""

            validate = item.getInfo(uncompprefix+"validate")
            if validate:
                valid, reason = validate(item.getOriginalURL(),
                                         localpath, withreason=True)
                if valid is not None:
                    if withreason:
                        return valid, reason
                    else:
                        return valid

            size = item.getInfo(uncompprefix+"size")
            if size:
                lsize = os.path.getsize(localpath)
                if lsize != size:
                    raise Error, "Unexpected size (expected %d, got %d)" % \
                                 (size, lsize)

            filemd5 = item.getInfo(uncompprefix+"md5")
            if filemd5:
                import md5
                digest = md5.md5()
                file = open(localpath)
                data = file.read(BLOCKSIZE)
                while data:
                    digest.update(data)
                    data = file.read(BLOCKSIZE)
                lfilemd5 = digest.hexdigest()
                if lfilemd5 != filemd5:
                    raise Error, "Invalid MD5 (expected %s, got %s)" % \
                                 (filemd5, lfilemd5)
            else:
                filesha = item.getInfo(uncompprefix+"sha")
                if filesha:
                    import sha
                    digest = sha.sha()
                    file = open(localpath)
                    data = file.read(BLOCKSIZE)
                    while data:
                        digest.update(data)
                        data = file.read(BLOCKSIZE)
                    lfilesha = digest.hexdigest()
                    if lfilesha != filesha:
                        raise Error, "Invalid SHA (expected %s, got %s)" % \
                                     (filesha, lfilesha)
        except Error, reason:
            if withreason:
                return False, reason
            return False
        else:
            if withreason:
                return True, None
            return True

class FetchItem(object):

    def __init__(self, fetcher, url, mirror):
        self._fetcher = fetcher
        self._url = url
        self._mirror = mirror
        self._urlobj = URL(mirror.getNext())
        self._retries = 0
        self._starttime = None

        self._info = {}

        self._status = WAITING
        self._failedreason = None
        self._targetpath = None

        self._progress = iface.getSubProgress(fetcher)

    def reset(self):
        self._status = WAITING
        self._failedreason = None
        self._targetpath = None
        self._starttime = None
        url = self._urlobj.original
        if self._progress.getSub(url):
            self._progress.setSubStopped(url)
            self._progress.show()
            self._progress.resetSub(url)

    def getRetries(self):
        return self._retries

    def setNextURL(self):
        self._retries += 1
        url = self._mirror.getNext()
        if url:
            self._urlobj.set(url)
            return True
        else:
            self._urlobj.set(self._url)
            return False

    def getOriginalURL(self):
        return self._url

    def getURL(self):
        return self._urlobj

    def setURL(self, url):
        self._urlobj.set(url)

    def getStatus(self):
        return self._status

    def getFailedReason(self):
        return self._failedreason

    def getTargetPath(self):
        return self._targetpath

    def getInfo(self, kind, default=None):
        return self._info.get(kind, default)

    def setInfo(self, **info):
        # Known used info kinds:
        #
        # - validate: validate function, it must accept a 'withreason'
        #             keyword, and must return either 'valid, reason'
        #             or just 'valid', depending on 'withreason'. 'valid'
        #             may be None, True, or False. If it's True or False,
        #             no other information will be checked.
        # - md5, sha: file digest
        # - size: file size
        # - uncomp: whether to uncompress or not
        # - uncomp_{md5,sha,size}: uncompressed equivalents
        #
        for kind in ("md5", "sha", "uncomp_md5", "uncomp_sha"):
            value = info.get(kind)
            if value:
                info[kind] = value.lower()
        self._info.update(info)

    def start(self):
        if self._status is RUNNING:
            return
        self._status = RUNNING
        self._starttime = time.time()
        prog = self._progress
        url = self._urlobj.original
        prog.setSubTopic(url, url)
        prog.setSubTopic(url, re.sub("([a-z]+:/+[^:/]+:)[^/]+(@.*)",
                                     r"\1*\2", url))
        prog.setSub(url, 0, self._info.get("size") or 1, 1)
        prog.show()

    def progress(self, current, total):
        if total:
            self._progress.setSub(self._urlobj.original, current, total, 1)
            self._progress.show()

    def setSucceeded(self, targetpath, fetchedsize=0):
        self._status = SUCCEEDED
        self._targetpath = targetpath
        if self._starttime:
            if fetchedsize:
                self._mirror.addInfo(time=time.time()-self._starttime,
                                     size=fetchedsize)
            self._progress.setSubDone(self._urlobj.original)
            self._progress.show()

    def setFailed(self, reason):
        self._status = FAILED
        self._failedreason = reason
        if self._starttime:
            self._mirror.addInfo(failed=1)
            self._progress.setSubStopped(self._urlobj.original)
            self._progress.show()

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
        if ":/" not in url:
            raise Error, "Invalid URL: %s" % url
        self.scheme, rest = urllib.splittype(url)
        if self.scheme in LOCALSCHEMES:
            scheme = self.scheme
            self.reset()
            self.scheme = scheme
            self.original = url
            self.path = os.path.normpath(rest)
            if self.path.startswith("//"):
                self.path = self.path[1:]
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
        self.user = self.user and urllib.unquote(self.user) or ""
        self.passwd = self.passwd and urllib.unquote(self.passwd) or ""
        self.path = urllib.unquote(self.path)

    def __str__(self):
        if self.scheme in LOCALSCHEMES:
            return "%s://%s" % (self.scheme, urllib.quote(self.path))
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

class FetcherHandler(object):
    def __init__(self, fetcher):
        self._fetcher = fetcher
        self._queue = []

    def getQueue(self):
        return self._queue

    def enqueue(self, item):
        self._queue.append(item)

    def dequeue(self, item):
        self._queue.remove(item)

    def start(self):
        self._queue.sort()

    def stop(self):
        pass

    def tick(self):
        return False

    def getLocalPath(self, item):
        return self._fetcher.getLocalPath(item)

    def runLocal(self, caching=None):
        fetcher = self._fetcher
        if not caching:
            caching = fetcher.getCaching()
        if caching is not NEVER:
            uncompressor = fetcher.getUncompressor()
            for i in range(len(self._queue)-1,-1,-1):
                item = self._queue[i]
                localpath = self.getLocalPath(item)
                uncomphandler = uncompressor.getHandler(localpath)
                if uncomphandler and item.getInfo("uncomp"):
                    uncomppath = uncomphandler.getTargetPath(localpath)
                    valid, reason = fetcher.validate(item, uncomppath,
                                                     withreason=True,
                                                     uncomp=True)
                    if valid and not fetcher.hasStrongValidate(item, True):
                        valid, reason = fetcher.validate(item, localpath,
                                                         withreason=True)
                    localpath = uncomppath
                else:
                    valid, reason = fetcher.validate(item, localpath,
                                                     withreason=True)
                if valid:
                    del self._queue[i]
                    item.setSucceeded(localpath)
                elif caching is ALWAYS:
                    del self._queue[i]
                    item.setFailed(reason)

class FileHandler(FetcherHandler):

    RETRIES = 3

    def __init__(self, *args):
        FetcherHandler.__init__(self, *args)
        self._active = False

    def getLocalPath(self, item):
        if self._fetcher.getForceCopy():
            return FetcherHandler.getLocalPath(self, item)
        else:
            return item.getURL().path

    def runLocal(self):
        if self._fetcher.getForceCopy():
            FetcherHandler.runLocal(self)
        else:
            # First, handle compressed files without uncompressed
            # versions available.
            fetcher = self._fetcher
            uncompressor = fetcher.getUncompressor()
            for i in range(len(self._queue)-1,-1,-1):
                item = self._queue[i]
                localpath = self.getLocalPath(item)
                media = self._fetcher.getMediaSet() \
                                     .findMountPoint(localpath, subpath=True)
                if media:
                    media.mount()
                uncomphandler = uncompressor.getHandler(localpath)
                if (uncomphandler and not
                    os.path.isfile(uncomphandler.getTargetPath(localpath))):
                    valid, reason = fetcher.validate(item, localpath,
                                                     withreason=True)
                    if valid:
                        linkpath = self._fetcher.getLocalPath(item)
                        if os.path.isfile(linkpath):
                            os.unlink(linkpath)
                        os.symlink(localpath, linkpath)
                        uncomppath = uncomphandler.getTargetPath(linkpath)
                        uncomphandler.uncompress(linkpath)
                        valid, reason = fetcher.validate(item, uncomppath,
                                                         withreason=True,
                                                         uncomp=True)
                        os.unlink(linkpath)
                    if valid:
                        item.setSucceeded(uncomppath)
                    else:
                        item.setFailed(reason)
                    del self._queue[i]

            # Then, everything else.
            FetcherHandler.runLocal(self, caching=ALWAYS)

    def tick(self):
        if self._queue and not self._active:
            self._active = True
            thread.start_new_thread(self.copy, ())
        return self._active

    def copy(self):
        while self._queue:
            item = self._queue.pop(0)
            item.start()
            retries = 0
            filepath = item.getURL().path
            localpath = self.getLocalPath(item)
            assert filepath != localpath
            while retries < self.RETRIES:
                try:
                    input = open(filepath)
                    output = open(localpath, "w")
                    while True:
                        data = input.read(BLOCKSIZE)
                        if not data:
                            break
                        output.write(data)
                except (IOError, OSError), e:
                    error = str(e)
                    retries += 1
                else:
                    item.setSucceeded(localpath)
                    break
            else:
                item.setFailed(error)
        self._active = False

Fetcher.setHandler("file", FileHandler)

class LocalMediaHandler(FileHandler):

    def runLocal(self):
        if not self._fetcher.getForceCopy():
            # When not copying, convert earlier to get local files
            # from the media.
            self.convertToFile()
        FileHandler.runLocal(self)

    def start(self):
        self.convertToFile()
        FileHandler.start(self)

    def convertToFile(self):
        mediaset = self._fetcher.getMediaSet()
        for i in range(len(self._queue)-1,-1,-1):
            item = self._queue[i]
            itempath = item.getURL().path
            media = item.getInfo("media")
            if not media:
                media = mediaset.getDefault()
                if media:
                    media.mount()
                else:
                    mediaset.mountAll()
                    media = mediaset.findFile(itempath)
                if not media or not media.isMounted():
                    item.setFailed("Media not found")
                    del self._queue[i]
                    continue
            item.setURL(media.joinURL(itempath))

Fetcher.setHandler("localmedia", LocalMediaHandler)

class FTPHandler(FetcherHandler):

    MAXACTIVE = 5
    MAXINACTIVE = 5
    MAXPERHOST = 2

    TIMEOUT = 60

    def __init__(self, *args):
        FetcherHandler.__init__(self, *args)
        self._active = {}   # ftp -> host
        self._inactive = {} # ftp -> (user, host, port)
        self._lock = thread.allocate_lock()

    def tick(self):
        import ftplib
        self._lock.acquire()
        if self._queue:
            if len(self._active) < self.MAXACTIVE:
                for i in range(len(self._queue)-1,-1,-1):
                    item = self._queue[i]
                    url = item.getURL()
                    hostactive = [x for x in self._active
                                  if self._active[x] == url.host]
                    if len(hostactive) < self.MAXPERHOST:
                        del self._queue[i]
                        userhost = (url.user, url.host, url.port)
                        for ftp in self._inactive:
                            if self._inactive[ftp] == userhost:
                                del self._inactive[ftp]
                                self._active[ftp] = url.host
                                thread.start_new_thread(self.fetch, (ftp, item))
                                break
                        else:
                            if len(self._inactive) > self.MAXINACTIVE:
                                del self._inactive[ftp]
                            ftp = ftplib.FTP()
                            ftp.lasttime = time.time()
                            self._active[ftp] = url.host
                            thread.start_new_thread(self.connect, (ftp, item))
        self._lock.release()
        return bool(self._queue or self._active)

    def connect(self, ftp, item):
        item.start()
        url = item.getURL()
        import socket, ftplib
        try:
            ftp.connect(url.host, url.port)
            ftp.login(url.user, url.passwd)
        except (socket.error, ftplib.Error), e:
            try:
                errmsg = str(e[1])
            except IndexError:
                errmsg = str(e)
            item.setFailed(errmsg)
            self._lock.acquire()
            del self._active[ftp]
            self._lock.release()
        else:
            self.fetch(ftp, item)

    def fetch(self, ftp, item):
        import socket, ftplib

        fetcher = self._fetcher
        url = item.getURL()

        item.start()

        try:
            try:
                ftp.cwd(os.path.dirname(url.path))
            except ftplib.Error:
                if ftp.lasttime+self.TIMEOUT < time.time():
                    raise EOFError
                raise

            filename = os.path.basename(url.path)
            localpath = self.getLocalPath(item)

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
                size = item.getInfo("size")
                if size and size != total:
                    raise Error, "Server reports unexpected size"

            if (not mtime or not os.path.isfile(localpath) or
                mtime != os.path.getmtime(localpath) or
                not fetcher.validate(item, localpath)):

                localpathpart = localpath+".part"
                if (os.path.isfile(localpathpart) and
                    (not total or os.path.getsize(localpathpart) < total)):
                    rest = os.path.getsize(localpathpart)
                    openmode = "a"
                    item.current = rest
                else:
                    rest = None
                    openmode = "w"
                    item.current = 0

                try:
                    local = open(localpathpart, openmode)
                except (IOError, OSError), e:
                    raise Error, "%s: %s" % (localpathpart, e)

                def write(data):
                    local.write(data)
                    item.current += len(data)
                    item.progress(item.current, total)

                try:
                    ftp.retrbinary("RETR "+filename, write, BLOCKSIZE, rest)
                finally:
                    local.close()

                if mtime:
                    os.utime(localpathpart, (mtime, mtime))

                os.rename(localpathpart, localpath)

                valid, reason = fetcher.validate(item, localpath,
                                                 withreason=True)
                if not valid:
                    if openmode == "a":
                        # Try again, from the very start.
                        item.reset()
                        self._lock.acquire()
                        self._queue.append(item)
                        self._lock.release()
                    else:
                        raise Error, reason
                else:
                    if total:
                        fetchedsize = total-(rest or 0)
                    elif not rest:
                        fetchedsize = os.path.getsize(localpath)
                    else:
                        fetchedsize = None
                    item.setSucceeded(localpath, fetchedsize)
            else:
                item.setSucceeded(localpath)

        except (socket.error, EOFError):
            # Put it back on the queue, and kill this ftp object.
            self._lock.acquire()
            self._queue.append(item)
            del self._active[ftp]
            self._lock.release()
            return

        except (Error, IOError, OSError, ftplib.Error), e:
            item.setFailed(str(e))

        self._lock.acquire()
        ftp.lasttime = time.time()
        self._inactive[ftp] = (url.user, url.host, url.port)
        del self._active[ftp]
        self._lock.release()

Fetcher.setHandler("ftp", FTPHandler)

class URLLIBHandler(FetcherHandler):

    MAXACTIVE = 5

    def __init__(self, *args):
        FetcherHandler.__init__(self, *args)
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
        import urllib, rfc822

        class Opener(urllib.FancyURLopener):
            user = None
            passwd = None
            def prompt_user_passwd(self, host, realm):
                return self.user, self.passwd
            def http_error_default(self, url, fp, errcode, errmsg, headers):
                info = urllib.addinfourl(fp, headers, "http:" + url)
                info.errcode = errcode
                info.errmsg = errmsg
                return info

        opener = Opener()
        
        fetcher = self._fetcher

        while True:

            self._lock.acquire()
            if not self._queue:
                self._lock.release()
                break
            item = self._queue.pop()
            self._lock.release()

            url = item.getURL()

            opener.user = url.user
            opener.passwd = url.passwd

            item.start()

            try:

                localpath = self.getLocalPath(item)
                current = 0
                total = None

                size = item.getInfo("size")

                del opener.addheaders[:]

                if (os.path.isfile(localpath) and
                    fetcher.validate(item, localpath)):
                    mtime = os.path.getmtime(localpath)
                    opener.addheader("if-modified-since",
                                     rfc822.formatdate(mtime))

                localpathpart = localpath+".part"
                if os.path.isfile(localpathpart):
                    partsize = os.path.getsize(localpathpart)
                    if not size or partsize < size:
                        opener.addheader("range", "bytes=%d-" % partsize)
                else:
                    partsize = 0

                remote = opener.open(url.original)

                if hasattr(remote, "errcode") and remote.errcode == 416:
                    # Range not satisfiable, try again without it.
                    opener.addheaders = [x for x in opener.addheaders
                                         if x[0] != "range"]
                    remote = opener.open(url.original)

                if hasattr(remote, "errcode") and remote.errcode != 206:
                    # 206 = Partial Content
                    raise remote

                info = remote.info()

                if "content-length" in info:
                    total = int(info["content-length"])
                elif size:
                    total = size

                if "content-range" in info:
                    openmode = "a"
                    current = partsize
                    if "content-length" in info:
                        total += partsize
                else:
                    partsize = 0
                    openmode = "w"

                if size and total and size != total:
                    raise Error, "Server reports unexpected size"

                try:
                    local = open(localpathpart, openmode)
                except (IOError, OSError), e:
                    raise IOError, "%s: %s" % (localpathpart, e)

                try:
                    data = remote.read(BLOCKSIZE)
                    while data:
                        local.write(data)
                        current += len(data)
                        item.progress(current, total)
                        data = remote.read(BLOCKSIZE)
                finally:
                    local.close()
                    remote.close()

                os.rename(localpathpart, localpath)

                valid, reason = fetcher.validate(item, localpath,
                                                 withreason=True)
                if not valid:
                    if openmode == "a":
                        # Try again, from the very start.
                        item.reset()
                        self._lock.acquire()
                        self._queue.append(item)
                        self._lock.release()
                    else:
                        raise Error, reason
                else:
                    if total:
                        fetchedsize = total-partsize
                    elif not partsize:
                        fetchedsize = os.path.getsize(localpath)
                    else:
                        fetchedsize = None
                    item.setSucceeded(localpath, fetchedsize)

                    if "last-modified" in info:
                        mtimes = info["last-modified"]
                        mtimet = rfc822.parsedate(mtimes)
                        if mtimet:
                            mtime = time.mktime(mtimet)
                            os.utime(localpath, (mtime, mtime))

            except urllib.addinfourl, remote:
                if remote.errcode == 304: # Not modified
                    item.setSucceeded(localpath)
                else:
                    item.setFailed(remote.errmsg)

            except (IOError, OSError, Error), e:
                item.setFailed(str(e))

        self._lock.acquire()
        self._active -= 1
        self._lock.release()

#Fetcher.setHandler("ftp", URLLIBHandler)
Fetcher.setHandler("http", URLLIBHandler)
Fetcher.setHandler("https", URLLIBHandler)
Fetcher.setHandler("gopher", URLLIBHandler)

# This is not in use, since urllib2 is not thread safe, and
# the authentication scheme requires additional steps which
# are still not implemented. Also, we need some way to handle
# 206 returns without breaking out.
"""
class URLLIB2Handler(FetcherHandler):

    MAXACTIVE = 1
    USECACHEDFTP = True

    _openerinstalled = False

    def __init__(self, *args):
        FetcherHandler.__init__(self, *args)
        if not URLLIB2Handler._openerinstalled:
            from gepeto.util import urllib2
            URLLIB2Handler._openerinstalled = True
            handlerlist = []
            if self.USECACHEDFTP:
                handlerlist.append(urllib2.CacheFTPHandler)
            handlerlist.append(urllib2.GopherHandler)
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

        while True:

            self._lock.acquire()
            if not self._queue:
                self._lock.release()
                break
            item = self._queue.pop()
            self._lock.release()

            item.start()

            url = item.getURL()

            try:

                localpath = self.getLocalPath(item)
                current = 0
                total = None

                size = item.getInfo("size")

                request = urllib2.Request(url.original)
                if (os.path.isfile(localpath) and
                    fetcher.validate(item, localpath)):
                    mtime = os.path.getmtime(localpath)
                    request.add_header("if-modified-since",
                                       rfc822.formatdate(mtime))

                localpathpart = localpath+".part"
                if os.path.isfile(localpathpart):
                    partsize = os.path.getsize(localpathpart)
                    if not size or partsize < size:
                        request.add_header("range", "bytes=%d-" % partsize)
                else:
                    partsize = 0

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
                elif size:
                    total = size

                if "content-range" in info:
                    openmode = "a"
                    current = partsize
                    total += partsize
                else:
                    openmode = "w"

                if size and total and size != total:
                    raise Error, "Server reports unexpected size"

                try:
                    local = open(localpathpart, openmode)
                except (IOError, OSError), e:
                    raise IOError, "%s: %s" % (localpathpart, e)

                try:
                    data = remote.read(BLOCKSIZE)
                    while data:
                        local.write(data)
                        current += len(data)
                        item.progress(current, total)
                        data = remote.read(BLOCKSIZE)
                finally:
                    local.close()
                    remote.close()

                os.rename(localpathpart, localpath)

                valid, reason = fetcher.validate(url, localpath,
                                                 withreason=True)
                if not valid:
                    if openmode == "a":
                        # Try again, from the very start.
                        prog.setSubStopped(url)
                        prog.show()
                        prog.resetSub(url)
                        self._lock.acquire()
                        self._queue.append(url)
                        self._lock.release()
                    else:
                        raise Error, reason
                else:
                    if total:
                        fetchedsize = total-partsize
                    elif not partsize:
                        fetchedsize = os.path.getsize(localpath)
                    else:
                        fetchedsize = None
                    item.setSucceeded(localpath, fetchedsize)

                    if "last-modified" in info:
                        mtimes = info["last-modified"]
                        mtimet = rfc822.parsedate(mtimes)
                        if mtimet:
                            mtime = time.mktime(mtimet)
                            os.utime(localpath, (mtime, mtime))

            except urllib2.HTTPError, e:
                if e.code == 304: # Not modified
                    item.setSucceeded(localpath)
                else:
                    item.setFailed(str(e))

            except (IOError, OSError, Error), e:
                item.setFailed(str(e))

        self._lock.acquire()
        self._active -= 1
        self._lock.release()

#Fetcher.setHandler("ftp", URLLIB2Handler)
Fetcher.setHandler("http", URLLIB2Handler)
Fetcher.setHandler("https", URLLIB2Handler)
Fetcher.setHandler("gopher", URLLIB2Handler)
"""#"""

class PyCurlHandler(FetcherHandler):

    MAXACTIVE = 5
    MAXINACTIVE = 5
    MAXPERHOST = 2

    def __init__(self, *args):
        import pycurl
        FetcherHandler.__init__(self, *args)
        self._active = {}   # handle -> (scheme, host)
        self._inactive = {} # handle -> (user, host, port)
        self._running = False
        self._multi = pycurl.CurlMulti()
        self._lock = thread.allocate_lock()

    def tick(self):
        import pycurl

        if not self._running and self._queue:
            self._running = True
            thread.start_new_thread(self.perform, ())

        fetcher = self._fetcher
        multi = self._multi

        num = 1
        while num != 0:

            self._lock.acquire()
            num, succeeded, failed = multi.info_read()
            self._lock.release()

            for handle in succeeded:

                item = handle.item
                local = handle.local
                localpath = handle.localpath

                url = item.getURL()

                local.close()

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
                userhost = (url.user, url.host, url.port)
                self._inactive[handle] = userhost

                valid, reason = fetcher.validate(item, localpath,
                                                 withreason=True)
                if valid:
                    fetchedsize = handle.getinfo(pycurl.SIZE_DOWNLOAD)
                    item.setSucceeded(localpath, fetchedsize)
                elif handle.partsize:
                    self._queue.append(item)
                else:
                    item.setFailed(reason)

            for handle, errno, errmsg in failed:

                item = handle.item
                local = handle.local
                localpath = handle.localpath

                url = item.getURL()

                local.close()

                self._lock.acquire()
                multi.remove_handle(handle)
                self._lock.release()

                del self._active[handle]
                userhost = (url.user, url.host, url.port)
                self._inactive[handle] = userhost

                if handle.partsize and "byte ranges" in errmsg:
                    os.unlink(localpath+".part")
                    prog.resetSub(url.original)
                    self._queue.append(item)
                else:
                    item.setFailed(errmsg)


        if self._queue:
            if len(self._active) < self.MAXACTIVE:
                for i in range(len(self._queue)-1,-1,-1):
                    item = self._queue[i]
                    url = item.getURL()
                    schemehost = (url.scheme, url.host)
                    hostactive = [x for x in self._active
                                     if self._active[x] == schemehost]
                    if len(hostactive) < self.MAXPERHOST:
                        del self._queue[i]

                        userhost = (url.user, url.host, url.port)
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

                        localpath = self.getLocalPath(item)
                        localpathpart = localpath+".part"

                        size = item.getInfo("size")

                        if os.path.isfile(localpathpart):
                            partsize = os.path.getsize(localpathpart)
                            if size and partsize >= size:
                                partsize = 0
                        else:
                            partsize = 0
                        handle.partsize = partsize
                        if partsize:
                            openmode = "a"
                            handle.setopt(pycurl.RESUME_FROM_LARGE,
                                          long(partsize))
                        else:
                            openmode = "w"
                            handle.setopt(pycurl.RESUME_FROM_LARGE, 0L)

                        try:
                            local = open(localpathpart, openmode)
                        except (IOError, OSError), e:
                            item.setFailed("%s: %s" % (localpathpart, e))

                        handle.item = item
                        handle.local = local
                        handle.localpath = localpath

                        item.start()

                        def progress(downtotal, downcurrent,
                                     uptotal, upcurrent, item=item,
                                     size=size, partsize=partsize):
                            if not downtotal:
                                if size and downcurrent:
                                    item.progress(partsize+downcurrent, size)
                            else:
                                item.progress(partsize+downcurrent,
                                              partsize+downtotal)

                        handle.setopt(pycurl.URL, url)
                        handle.setopt(pycurl.OPT_FILETIME, 1)
                        handle.setopt(pycurl.NOPROGRESS, 0)
                        handle.setopt(pycurl.PROGRESSFUNCTION, progress)
                        handle.setopt(pycurl.WRITEDATA, local)

                        if fetcher.validate(item, localpath):
                            handle.setopt(pycurl.TIMECONDITION,
                                          pycurl.TIMECOND_IFMODSINCE)
                            mtime = os.path.getmtime(localpath)
                            if url.scheme == "ftp":
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
        self._running = False

try:
    import pycurl
except ImportError:
    pass
else:
    schemes = pycurl.version_info()[-1]
    for scheme in schemes:
        if scheme != "file":
            Fetcher.setHandler(scheme, PyCurlHandler)

class SCPHandler(FetcherHandler):

    MAXACTIVE = 5
    MAXPERHOST = 2

    def __init__(self, *args):
        FetcherHandler.__init__(self, *args)
        self._active = [] # item
        self._lock = thread.allocate_lock()

    def tick(self):
        import ftplib
        self._lock.acquire()
        if self._queue:
            if len(self._active) < self.MAXACTIVE:
                for i in range(len(self._queue)-1,-1,-1):
                    item = self._queue[i]
                    url = item.getURL()
                    hostactive = [x for x in self._active
                                  if x.getURL().host == url.host]
                    if len(hostactive) < self.MAXPERHOST:
                        del self._queue[i]
                        self._active.append(item)
                        item.total = None
                        item.localpath = None
                        thread.start_new_thread(self.fetch, (item,))
        prog = iface.getSubProgress(self._fetcher)
        for item in self._active:
            if item.total and item.localpath:
                try:
                    size = os.path.getsize(item.localpath)
                except OSError:
                    pass
                else:
                    item.progress(size, item.total)
        self._lock.release()
        return bool(self._queue or self._active)

    def fetch(self, item):
        from gepeto.util.ssh import SSH

        fetcher = self._fetcher
        prog = iface.getSubProgress(self._fetcher)

        item.start()

        url = item.getURL()

        if not url.user:
            import pwd
            url.user = pwd.getpwuid(os.getuid()).pw_name

        if url.host[-1] == ":":
            url.host = url.host[:-1]
        ssh = SSH(url.user, url.host, url.passwd)

        try:
            localpath = self.getLocalPath(item)

            mtime = None
            total = None

            size = item.getInfo("size")

            status, output = ssh.ssh("stat -c '%%Y %%s' %s" % url.path)
            if status == 0:
                tokens = output.split()
                try:
                    mtime = int(tokens[0])
                    total = int(tokens[1])
                except ValueError:
                    if size:
                        total = size
                else:
                    if size and size != total:
                        raise Error, "Server reports unexpected size"
            elif size:
                total = size

            item.total = total

            fetchedsize = 0

            if (not mtime or not os.path.isfile(localpath) or
                mtime != os.path.getmtime(localpath) or
                not fetcher.validate(item, localpath)):

                item.localpath = localpath+".part"

                status, output = ssh.rscp(url.path, item.localpath)
                if status != 0:
                    raise Error, output

                os.rename(item.localpath, localpath)

                fetchedsize = os.path.getsize(localpath)

                if mtime:
                    os.utime(localpath, (mtime, mtime))

                valid, reason = fetcher.validate(item, localpath,
                                                 withreason=True)
                if not valid:
                    raise Error, reason

        except (Error, IOError, OSError), e:
            item.setFailed(str(e))
        else:
            item.setSucceeded(localpath, fetchedsize)

        self._lock.acquire()
        self._active.remove(item)
        self._lock.release()

Fetcher.setHandler("scp", SCPHandler)

# vim:ts=4:sw=4:et

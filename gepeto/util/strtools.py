import posixpath
import string

class ShortURL(object):
    def __init__(self, maxlen):
        self._cache = {}
        self._maxlen = maxlen

    def reset(self):
        self._cache.clear()

    def get(self, url):
        shorturl = self._cache.get(url)
        if not shorturl:
            if len(url) > self._maxlen and url.count("/") > 3:
                dir, base = posixpath.split(url)
                while len(dir)+len(base)+5 > self._maxlen:
                    if dir.count("/") < 3:
                        break
                    dir, _ = posixpath.split(dir)
                shorturl = posixpath.join(dir, ".../", base)
            else:
                shorturl = url
            self._cache[url] = shorturl
        return shorturl

def getSizeStr(bytes):
    if bytes < 1000:
        return "%db" % bytes
    elif bytes < 1000000:
        return "%.1fk" % (bytes/1000.)
    else:
        return "%.1fM" % (bytes/1000000.)

_nulltrans = string.maketrans('', '')
def isRegEx(s):
    return s.translate(_nulltrans, '^{[*') != s

def strToBool(s, default=False):
    if not s:
        return default
    s = s.strip().lower()
    if s in ("y", "yes", "true", "1"):
        return True
    if s in ("n", "no", "false", "0"):
        return False
    return default


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


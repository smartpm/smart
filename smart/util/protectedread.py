#
# Copyright (c) 2005 Canonical
#
# Written by Gustavo Niemeyer <gustavo@niemeyer.net>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
import codecs

def protectedread(self, size=-1, chars=-1):

    if not hasattr(self, "charbuffer"):
        self.charbuffer = u""
        self.bytebuffer = u""
        self.linebuffer = None
    elif self.linebuffer:
        self.charbuffer = "".join(self.linebuffer)
        self.linebuffer = None

    while True:
        if chars < 0:
            if self.charbuffer:
                break
        else:
            if len(self.charbuffer) >= chars:
                break
        if size < 0:
            newdata = self.stream.read()
        else:
            newdata = self.stream.read(size)
        data = self.bytebuffer + newdata
        # That's the only change introduced in the default
        # read method.
        while True:
            try:
                newchars, decodedbytes = self.decode(data, self.errors)
            except UnicodeDecodeError, e:
                data = data[:e.start]+'?'+data[e.start+1:]
            else:
                break
        self.bytebuffer = data[decodedbytes:]
        self.charbuffer += newchars
        if not newdata:
            break
    if chars < 0:
        result = self.charbuffer
        self.charbuffer = u""
    else:
        result = self.charbuffer[:chars]
        self.charbuffer = self.charbuffer[chars:]
    return result

codecs.StreamReader.read = protectedread

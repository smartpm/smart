#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
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

class TagFile(dict):

    def __init__(self, filename):
        self._filename = filename
        self._file = open(filename)
        self._offset = 0

    def setOffset(self, offset):
        self._offset = offset
        self._file.seek(offset)

    def getOffset(self):
        return self._offset

    def advanceSection(self):
        try:
            self.clear()
            key = None
            for line in self._file:
                self._offset += len(line)
                line = line.rstrip()
                if not line:
                    break
                if line[0].isspace():
                    if key:
                        self[key] += "\n"+line.lstrip()
                else:
                    toks = line.split(":", 1)
                    if len(toks) == 2:
                        key = toks[0].strip().lower()
                        self[key] = toks[1].strip()
                    else:
                        key = None
        except StopIteration:
            pass
        return bool(self)

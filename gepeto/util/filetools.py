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
from gepeto.const import BLOCKSIZE
import md5, os

def compareFiles(path1, path2):
    if not os.path.isfile(path1) or not os.path.isfile(path2):
        return False
    if os.path.getsize(path1) != os.path.getsize(path2):
        return False
    path1sum = md5.md5()
    path2sum = md5.md5()
    for path, sum in [(path1, path1sum), (path2, path2sum)]:
        file = open(path)
        while True:
            data = file.read(BLOCKSIZE)
            if not data:
                break
            sum.update(data)
        file.close()
    if path1sum.digest() != path2sum.digest():
        return False
    return True

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
import sys

VERSION = "0.12"

RECURSIONLIMIT = sys.getrecursionlimit()

class Enum(object):
    def __init__(self, name):
        self._name = name
    def __repr__(self):
        return self._name

INSTALL   = Enum("INSTALL")
REMOVE    = Enum("REMOVE")

KEEP      = Enum("KEEP")
REINSTALL = Enum("REINSTALL")
UPGRADE   = Enum("UPGRADE")
FIX       = Enum("FIX")

OPTIONAL  = Enum("OPTIONAL")
NEVER     = Enum("NEVER")
ENFORCE   = Enum("ENFORCE")
ALWAYS    = Enum("ALWAYS")

ERROR     = Enum("ERROR")
WARNING   = Enum("WARNING")
INFO      = Enum("INFO")
DEBUG     = Enum("DEBUG")

WAITING   = Enum("WAITING")
RUNNING   = Enum("RUNNING")
FAILED    = Enum("FAILED")
SUCCEEDED = Enum("SUCCEEDED")

BLOCKSIZE = 16384

DISTROFILE = "/usr/lib/smart/distro.py"
DATADIR    = "/var/lib/smart/"
CONFFILE   = "config"

# vim:ts=4:sw=4:et

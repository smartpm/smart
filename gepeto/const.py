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

VERSION = "0.12"

INSTALL = 1
REMOVE  = 2

KEEP      = 3
REINSTALL = 4
UPGRADE   = 5
FIX       = 6

OPTIONAL = 1
NEVER    = 2
ALWAYS   = 3

ERROR   = 1
WARNING = 2
INFO    = 3
DEBUG   = 4

WAITING   = 1
RUNNING   = 2
FAILED    = 3
SUCCEEDED = 4

BLOCKSIZE = 16384

DISTROFILE = "/usr/lib/gepeto/distro.py"
DATADIR = "/var/lib/gepeto/"
CONFFILE = "config"

# vim:ts=4:sw=4:et

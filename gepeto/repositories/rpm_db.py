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
from cpm.backends.rpm.header import RPMDBLoader
from cpm.repository import Repository

class RPMDBRepository(Repository):

    def fetch(self, fetcher):
        self._loader = RPMDBLoader()
        self._loader.setRepository(self)

def create(reptype, data):
    name = None
    if type(data) is dict:
        name = data.get("name")
    elif hasattr(data, "tag") and data.tag == "repository":
        name = data.get("name")
    else:
        raise RepositoryDataError
    if not name:
        raise Error, "repository of type '%s' has no name" % reptype
    return RPMDBRepository(reptype, name)

# vim:ts=4:sw=4:et

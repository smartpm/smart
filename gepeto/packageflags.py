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

class PackageFlags(object):

    _matchers = {}

    def __init__(self, map):
        self._map = map
    
    def add(self, flag, name, version=None, relation=None):
        names = self._map.get(flag)
        if names:
            lst = names.get(name)
            if lst:
                lst.append((relation, version))
            else:
                names[name] = [(relation, version)]
        else:
            self._map[flag] = {name: [(relation, version)]}

    def test(self, flag, pkg):
        names = self._map.get(flag)
        if names:
            lst = names.get(pkg.name)
            if lst:
                for item in lst:
                    if pkg.matches(*item):
                        return True
        return False

    def filter(self, flag, pkgs):
        fpkgs = []
        names = self._map.get(flag)
        if names:
            for pkg in pkgs:
                lst = names.get(pkg.name)
                if lst:
                    for item in lst:
                        if pkg.matches(*item):
                            fpkgs.append(pkg)
                            break
        return fpkgs

# vim:ts=4:sw=4:et

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

class Matcher(object):
    def __init__(self, str):
        self._str = str

    def matches(self, obj):
        return False

class MasterMatcher(object):
    def __init__(self, str):
        self._str = str
        self._matchers = {}

    def matches(self, obj):
        if hasattr(obj, "matcher"):
            matcher = self._matchers.get(obj.matcher)
            if not matcher:
                matcher = obj.matcher(self._str)
                self._matchers[obj.matcher] = matcher
            return matcher.matches(obj)
        return False

    def filter(self, lst):
        return [x for x in lst if self.matches(x)]

# vim:ts=4:sw=4:et

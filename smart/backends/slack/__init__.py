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
from smart.backends.slack.pm import SlackPackageManager
from slackver import checkdep, vercmp
from smart.util.strtools import isGlob
from smart.matcher import Matcher
from smart.cache import *
import fnmatch
import string
import os, re

__all__ = ["SlackPackage", "SlackProvides", "SlackUpgrades"]

class SlackMatcher(Matcher):

    def __init__(self, str):
        Matcher.__init__(self, str)
        self._options = [] # (name, version)
        # First, try to match the whole thing against the name.
        name = str
        if isGlob(name):
            try:
                name = re.compile(fnmatch.translate(name))
            except re.error:
                pass
        self._options.append((name, None))
        tokens = str.split("-")
        if len(tokens) > 1:
            # Then, consider the last section as the version.
            name = "-".join(tokens[:-1])
            if isGlob(name):
                try:
                    name = re.compile(fnmatch.translate(name))
                except re.error:
                    pass
            version = tokens[-1]
            if isGlob(version):
                try:
                    version = re.compile(fnmatch.translate(version))
                except re.error:
                    pass
            self._options.append((name, version))
            # Now, consider last two sections as the version.
            if len(tokens) > 2:
                name = "-".join(tokens[:-2])
                if isGlob(name):
                    try:
                        name = re.compile(fnmatch.translate(name))
                    except re.error:
                        pass
                version = "-".join(tokens[-2:])
                if isGlob(version):
                    try:
                        version = re.compile(fnmatch.translate(version))
                    except re.error:
                        pass
                self._options.append((name, version))
                # Finally, consider last three sections as the version.
                if len(tokens) > 3:
                    name = "-".join(tokens[:-3])
                    if isGlob(name):
                        try:
                            name = re.compile(fnmatch.translate(name))
                        except re.error:
                            pass
                    version = "-".join(tokens[-3:])
                    if isGlob(version):
                        try:
                            version = re.compile(fnmatch.translate(version))
                        except re.error:
                            pass
                    self._options.append((name, version))

    def matches(self, obj):
        for name, version in self._options:
            if type(name) is str:
                if name != obj.name:
                    continue
            else:
                if not name.match(obj.name):
                    continue
            if version:
                if type(version) is str:
                    if vercmp(version, obj.version) != 0:
                        continue
                elif not version.match(obj.version):
                    continue
            return True

class SlackPackage(Package):

    packagemanager = SlackPackageManager
    matcher = SlackMatcher

    def matches(self, relation, version):
        if not relation:
            return True
        return checkdep(self.version, relation, version)

    def coexists(self, other):
        if not isinstance(other, SlackPackage):
            return True
        return False

    def __lt__(self, other):
        rc = -1
        if type(other) is SlackPackage:
            rc = cmp(self.name, other.name)
            if rc == 0 and self.version != other.version:
                rc = vercmp(self.version, other.version)
        return rc == -1

class SlackProvides(Provides): pass

class SlackDepends(Depends):

    def matches(self, prv):
        if not isinstance(prv, SlackProvides):
            return False
        if not self.version or not prv.version:
            return True
        return checkdep(prv.version, self.relation, self.version)

class SlackUpgrades(SlackDepends,Upgrades): pass

# vim:ts=4:sw=4:et

from cpm.backends.rpm.pm import RPMPackageManager
#from rpmver import checkdep, vercmp, splitarch
from crpmver import checkdep, vercmp, splitarch
from cpm.matcher import Matcher
from cpm.cache import *
import string
import os, re

from rpm import archscore

__all__ = ["RPMPackage", "RPMProvides", "RPMNameProvides",
           "RPMRequires", "RPMUpgrades", "RPMConflicts", "RPMObsoletes"]

class RPMMatcher(Matcher):
    def __init__(self, str):
        Matcher.__init__(self, str)
        self._options = [] # (name, version)
        nulltrans = string.maketrans('', '')
        isre = lambda x: x.translate(nulltrans, '^{[*') != x
        # First, try to match the whole thing against the name.
        if isre(str):
            name = re.compile(str)
        else:
            name = str
        self._options.append((name, None))
        tokens = str.split("-")
        if len(tokens) > 1:
            # Then, consider the last section as the version.
            name = "-".join(tokens[:-1])
            if isre(name):
                name = re.compile(name)
            version = tokens[-1]
            if isre(version):
                if ":" not in version and version[0].isdigit():
                    version = "(?:\d+:)?"+version
                version = re.compile(version)
            self._options.append((name, version))
            # Finally, consider last two sections as the version.
            if len(tokens) > 2:
                name = "-".join(tokens[:-2])
                if isre(name):
                    name = re.compile(name)
                version = "-".join(tokens[-2:])
                if isre(version):
                    if ":" not in version and version[0].isdigit():
                        version = "(?:\d+:)?"+version
                    version = re.compile(version)
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
                    if ":" not in version and ":" in obj.version:
                        ov = obj.version
                        version = ov[:ov.find(":")+1]+version
                    objver, objarch = splitarch(obj.version)
                    if vercmp(version, objver) != 0:
                        ver, arch = splitarch(version)
                        if arch != objarch or vercmp(ver, objver) != 0:
                            continue
                elif not version.match(obj.version):
                    continue
            return True

class RPMPackage(Package):

    packagemanager = RPMPackageManager
    matcher = RPMMatcher

    def coexists(self, other):
        if type(other) is not RPMPackage:
            return True
        # Do not accept two archs at the same time for now
        selfver, selfarch = splitarch(self.version)
        otherver, otherarch = splitarch(other.version)
        return selfver != otherver

    def matches(self, relation, version):
        if not relation:
            return True
        return checkdep(self.version, relation, version)

    def __cmp__(self, other):
        rc = -1
        if type(other) is RPMPackage:
            rc = cmp(self.name, other.name)
            if rc == 0 and self.version != other.version:
                selfver, selfarch = splitarch(self.version)
                otherver, otherarch = splitarch(other.version)
                if selfver != otherver:
                    rc = vercmp(self.version, other.version)
                if rc == 0:
                    rc = -cmp(archscore(selfarch), archscore(otherarch))
        return rc

class RPMProvides(Provides): pass
class RPMNameProvides(RPMProvides): pass

class RPMDepends(Depends):

    def matches(self, prv):
        if self.name != prv.name:
            return False
        if not self.version or not prv.version:
            return True
        return checkdep(prv.version, self.relation, self.version)

class RPMRequires(RPMDepends,Requires): pass
class RPMUpgrades(RPMDepends,Upgrades): pass
class RPMConflicts(RPMDepends,Conflicts): pass

class RPMObsoletes(Depends):

    def matches(self, prv):
        if prv.__class__ != RPMNameProvides:
            return False
        if self.name != prv.name:
            return False
        if self.version and not prv.version:
            return False
        if not self.version and prv.version:
            return True
        return checkdep(prv.version, self.relation, self.version)

# vim:ts=4:sw=4:et

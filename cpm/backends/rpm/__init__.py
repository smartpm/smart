from cpm.backends.rpm.pm import RPMPackageManager
#from rpmver import checkdep, vercmp
from crpmver import checkdep, vercmp
from cpm.matcher import Matcher
from cpm.cache import *
import string
import os, re

__all__ = ["RPMPackage", "RPMProvides", "RPMNameProvides", "RPMRequires",
           "RPMObsoletes", "RPMConflicts"]

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
                    if vercmp(version, obj.version) != 0:
                        if ":" not in version and ":" in obj.version:
                            ov = obj.version
                            version = ov[:ov.find(":")+1]+version
                            if vercmp(version, obj.version) != 0:
                                continue
                        else:
                            continue
                elif not version.match(obj.version):
                    continue
            return True

class RPMPackage(Package):

    packagemanager = RPMPackageManager
    matcher = RPMMatcher

    def __cmp__(self, other):
        rc = -1
        if isinstance(other, Package):
            rc = cmp(self.name, other.name)
            if rc == 0:
                rc = vercmp(self.version, other.version)
        return rc

class RPMProvides(Provides): pass
class RPMNameProvides(RPMProvides): pass

class RPMDepends(Depends):

    def matches(self, prov):
        if self.name != prov.name:
            return False
        if not self.version or not prov.version:
            return True
        return checkdep(prov.version, self.relation, self.version)

class RPMObsoletes(RPMDepends,Obsoletes):

    def matches(self, prov):
        if prov.__class__ != RPMNameProvides:
            return False
        if self.name != prov.name:
            return False
        if self.version and not prov.version:
            return False
        if not self.version and prov.version:
            return True
        return checkdep(prov.version, self.relation, self.version)

class RPMRequires(RPMDepends,Requires): pass
class RPMConflicts(RPMDepends,Conflicts): pass

# vim:ts=4:sw=4:et

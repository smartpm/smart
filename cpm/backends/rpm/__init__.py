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
        if '=' in str:
            name, version = str.split('=')
        else:
            name = str
            version = None
        nulltrans = string.maketrans('', '')
        isre = lambda x: x.translate(nulltrans, '^{[*') != x
        if isre(name):
            self._name = re.compile(name)
        else:
            self._name = name
        if version and isre(version):
            self._version = re.compile(version)
        else:
            self._version = version

    def matches(self, obj):
        if isinstance(self._name, str):
            if self._name != obj.name:
                return False
        elif not self._name.match(obj.name):
            return False
        if isinstance(self._version, str):
            if vercmp(self._version, obj.version) != 0:
                return False
        elif self._version and not self._version.match(obj.version):
            return False
        return True

class RPMPackage(Package):

    packagemanager = RPMPackageManager
    matcher = RPMMatcher

    def getInfo(self):
        return self._loader.getInfo(self)

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

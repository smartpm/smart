from epm.cache import *
#from rpmver import checkdep
from crpmver import checkdep
import os

__all__ = ["RPMPackage", "RPMProvides", "RPMDepends", "RPMLoader"]

class RPMPackage(Package): pass

class RPMProvides(Provides): pass

class RPMDepends(Depends):
    def matches(self, prov):
        if self.name != prov.name:
            return False
        if not self.version or not prov.version:
            return True
        return checkdep(prov.version, self.relation, self.version)

class RPMLoader(Loader):
    Package = RPMPackage
    Provides = RPMProvides
    Requires = RPMDepends
    Obsoletes = RPMDepends
    Conflicts = RPMDepends

# vim:ts=4:sw=4:et

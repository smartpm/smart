from epm.cache import *
#from rpmver import checkdep, vercmp
from crpmver import checkdep, vercmp
import os

__all__ = ["RPMPackage", "RPMProvides", "RPMDepends", "RPMLoader"]

class RPMPackage(Package):

    def getInfo(self):
        return self._loader.getInfo(self)

    def __cmp__(self, other):
        rc = -1
        if isinstance(other, Package):
            rc = cmp(self.name, other.name)
            if rc == 0:
                rc = vercmp(self.version, other.version)
        return rc

class RPMProvides(Provides):

    def getObsoletedBy(self):
        lst = []
        for obs in self.obsoletedby:
            lst.append((obs, [x for x in obs.packages
                                 if x.name == obs.name]))
        return lst

class RPMDepends(Depends):

    def matches(self, prov):
        if self.name != prov.name:
            return False
        if not self.version or not prov.version:
            return True
        return checkdep(prov.version, self.relation, self.version)

class RPMObsoletes(RPMDepends,Obsoletes):

    def getProvidedBy(self):
        lst = []
        for prv in self.providedby:
            lst.append((prv, [x for x in prv.packages
                                 if x.name == prv.name]))
        return lst

    def matches(self, prov):
        if self.name != prov.name:
            return False
        if self.version and not prov.version:
            return False
        if not self.version and prov.version:
            return True
        return checkdep(prov.version, self.relation, self.version)

class RPMRequires(RPMDepends,Requires): pass
class RPMConflicts(RPMDepends,Conflicts): pass

class RPMLoader(Loader):
    Package = RPMPackage
    Provides = RPMProvides
    Requires = RPMRequires
    Obsoletes = RPMObsoletes
    Conflicts = RPMConflicts

# vim:ts=4:sw=4:et

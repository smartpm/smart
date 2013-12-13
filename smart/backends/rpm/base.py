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

# Import it before rpm to avoid segfault with zlib symbols
# being linked with rpm. :-(
import zlib

from rpmver import checkdep, checkver, vercmp, splitarch, splitrelease
from smart.util.strtools import isGlob
from smart.cache import *
from smart import *
import fnmatch
import string
import os, re

try:
    import rpm
except ImportError:
    from smart.const import DEBUG
    if sysconf.get("log-level") == DEBUG:
        import traceback
        traceback.print_exc()
    raise Error, _("'rpm' python module is not available")

__all__ = ["RPMPackage", "RPMProvides", "RPMNameProvides", "RPMPreRequires",
           "RPMRequires", "RPMUpgrades", "RPMConflicts", "RPMObsoletes",
           "rpm", "getTS", "getArchScore", "getArchColor", "system_provides",
           "collapse_libc_requires"]

def rpm_join_dbpath(root, dbpath):
    if dbpath.startswith('/') and root:
        return os.path.join(root, dbpath[1:])
    else:
        return os.path.join(root, dbpath)

def getTS(new=False):
    if sysconf.get("rpm-extra-macros"):
        for key, value in sysconf.get("rpm-extra-macros").items():
            rpm.addMacro(key, str(value))

    rpm_root = os.path.abspath(sysconf.get("rpm-root", "/"))
    if not hasattr(getTS, "ts") or getTS.root != rpm_root:
        getTS.root = rpm_root
        if sysconf.get("rpm-dbpath"):
            rpm.addMacro('_dbpath', "/" + sysconf.get("rpm-dbpath"))
        getTS.ts = rpm.ts(getTS.root)
        #if not sysconf.get("rpm-check-signatures", False):
        #    getTS.ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)
        rpm_dbpath = sysconf.get("rpm-dbpath", "var/lib/rpm")
        dbdir = rpm_join_dbpath(getTS.root, rpm_dbpath)
        if not os.path.isdir(dbdir):
            try:
                os.makedirs(dbdir)
            except (OSError), e:
                raise Error, _("Could not create rpm-root at %s: %s") \
                             % (dbdir, unicode(e))
        if not os.path.isfile(os.path.join(dbdir, "Packages")):
            try:
                getTS.ts.initDB()
            except (rpm.error, OSError):
                raise Error, _("Couldn't initizalize rpm database at %s") \
                             % getTS.root
            else:
                iface.warning(_("Initialized new rpm database at %s")
                              % getTS.root)
    if new:
        if sysconf.get("rpm-dbpath"):
            rpm.addMacro('_dbpath', "/" + sysconf.get("rpm-dbpath"))
        ts = rpm.ts(getTS.root)
        #if not sysconf.get("rpm-check-signatures", False):
        #    ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)
        return ts
    else:
        return getTS.ts

# Here because pm requires getTS and rpm defined/imported above.
from smart.backends.rpm.pm import RPMPackageManager

class RPMPackage(Package):

    __slots__ = ()

    packagemanager = RPMPackageManager

    def equals(self, other):
        if self.name != other.name or self.version != other.version:
            return False
        if Package.equals(self, other):
            return True
        fk = dict.fromkeys
        if (len(self.upgrades) != len(other.upgrades) or
            len(self.conflicts) != len(other.conflicts)):
            return False
        supgs = fk(self.upgrades)
        oupgs = fk(other.upgrades)
        if supgs != oupgs:
            for supg in supgs:
                if supg in oupgs:
                    continue
                for oupg in oupgs:
                    if (supg.name == oupg.name and
                        checkver(supg.version, oupg.version)):
                        break
                else:
                    return False
            for oupg in oupgs:
                if oupg in supgs:
                    continue
                for supg in supgs:
                    if (supg.name == oupg.name and
                        checkver(supg.version, oupg.version)):
                        break
                else:
                    return False
        scnfs = fk(self.conflicts)
        ocnfs = fk(other.conflicts)
        if scnfs != ocnfs:
            for scnf in scnfs:
                if scnf in ocnfs:
                    continue
                for ocnf in ocnfs:
                    if (scnf.name == ocnf.name and
                        checkver(scnf.version, ocnf.version)):
                        break
                else:
                    return False
            for ocnf in ocnfs:
                if ocnf in scnfs:
                    continue
                for scnf in scnfs:
                    if (scnf.name == ocnf.name and
                        checkver(scnf.version, ocnf.version)):
                        break
                else:
                    return False
        sprvs = fk(self.provides)
        oprvs = fk(other.provides)
        if sprvs != oprvs:
            for sprv in sprvs:
                if not sprv.name or sprv.name[0] == "/" or sprv in oprvs:
                    continue
                for oprv in oprvs:
                    if (sprv.name == oprv.name and
                        checkver(sprv.version, oprv.version)):
                        break
                else:
                    return False
            for oprv in oprvs:
                if not oprv.name or oprv.name[0] == "/" or oprv in sprvs:
                    continue
                for sprv in sprvs:
                    if (sprv.name == oprv.name and
                        checkver(sprv.version, oprv.version)):
                        break
                else:
                    return False
        sreqs = fk(self.requires)
        oreqs = fk(other.requires)
        if sreqs != oreqs:
            for sreq in sreqs:
                if sreq.name[0] == "/" or sreq in oreqs:
                    continue
                for oreq in oreqs:
                    if (sreq.name == oreq.name and
                        sreq.relation == oreq.relation and
                        checkver(sreq.version, oreq.version)):
                        break
                else:
                    return False
            for oreq in oreqs:
                if oreq.name[0] == "/" or oreq in sreqs:
                    continue
                for sreq in sreqs:
                    if (sreq.name == oreq.name and
                        sreq.relation == oreq.relation and
                        checkver(sreq.version, oreq.version)):
                        break
                else:
                    return False
        srecs = fk(self.recommends)
        orecs = fk(other.recommends)
        if srecs != orecs:
            for srec in srecs:
                if srec.name[0] == "/" or srec in orecs:
                    continue
                for orec in orecs:
                    if (srec.name == orec.name and
                        srec.relation == orec.relation and
                        checkver(srec.version, orec.version)):
                        break
                else:
                    return False
            for orec in orecs:
                if orec.name[0] == "/" or orec in srecs:
                    continue
                for srec in srecs:
                    if (srec.name == orec.name and
                        srec.relation == orec.relation and
                        checkver(srec.version, orec.version)):
                        break
                else:
                    return False
        return True

    def coexists(self, other):
        if not isinstance(other, RPMPackage):
            return True
        if self.version == other.version:
            return False
        selfver, selfarch = splitarch(self.version)
        otherver, otherarch = splitarch(other.version)
        if selfarch != otherarch:
            return True
        selfcolor = getArchColor(selfarch)
        othercolor = getArchColor(otherarch)
        if (selfcolor and othercolor and selfcolor != othercolor and
            not sysconf.get("rpm-strict-multilib")):
            return True
        if not pkgconf.testFlag("multi-version", self):
            return False
        return selfver != otherver

    def matches(self, relation, version):
        if not relation:
            return True
        selfver, selfarch = splitarch(self.version)
        ver, arch = splitarch(version)
        return checkdep(selfver, relation, ver)

    def search(self, searcher, _epochre=re.compile("[0-9]+:")):
        myname = self.name
        myversionwithepoch, myarch = splitarch(self.version)
        myversionwithoutepoch = _epochre.sub("", myversionwithepoch)
        ratio = 0
        ic = searcher.ignorecase
        for nameversion, cutoff in searcher.nameversion:
            if _epochre.search(nameversion):
                myversion = myversionwithepoch
            else:
                myversion = myversionwithoutepoch
            if '@' in nameversion:
                _, ratio1 = globdistance(nameversion, "%s-%s@%s" %
                                         (myname, myversion, myarch),
                                         cutoff, ic)
                _, ratio2 = globdistance(nameversion, "%s@%s" %
                                         (myname, myarch), cutoff, ic)
                _, ratio3 = globdistance(nameversion, "%s-%s@%s" %
                                         (myname, splitrelease(myversion)[0],
                                          myarch), cutoff, ic)
            else:
                _, ratio1 = globdistance(nameversion, myname, cutoff, ic)
                _, ratio2 = globdistance(nameversion,
                                         "%s-%s" % (myname, myversion),
                                         cutoff, ic)
                _, ratio3 = globdistance(nameversion, "%s-%s" %
                                         (myname, splitrelease(myversion)[0]),
                                         cutoff, ic)
            ratio = max(ratio, ratio1, ratio2, ratio3)
        if ratio:
            searcher.addResult(self, ratio)

    def __lt__(self, other):
        rc = cmp(self.name, other.name)
        if type(other) is RPMPackage:
            if rc == 0 and self.version != other.version:
                selfver, selfarch = splitarch(self.version)
                otherver, otherarch = splitarch(other.version)
                if selfarch != otherarch:
                    selfcolor = getArchColor(selfarch)
                    othercolor = getArchColor(otherarch)
                    if selfcolor and othercolor:
                        rc = cmp(selfcolor, othercolor)
                if rc == 0:
                    if selfver != otherver:
                        rc = vercmp(selfver, otherver)
                    if rc == 0:
                        rc = -cmp(getArchScore(selfarch), getArchScore(otherarch))
        return rc == -1

class RPMProvides(Provides):         __slots__ = ()
class RPMNameProvides(RPMProvides):  __slots__ = ()

class RPMDepends(Depends):

    __slots__ = ()

    def matches(self, prv):
        if not isinstance(prv, RPMProvides) and type(prv) is not Provides:
            return False
        if not self.version or not prv.version:
            return True
        selfver, selfarch = splitarch(self.version)
        prvver, prvarch = splitarch(prv.version)
        return checkdep(prvver, self.relation, selfver)

class RPMPreRequires(RPMDepends,PreRequires): __slots__ = ()
class RPMRequires(RPMDepends,Requires):       __slots__ = ()
class RPMUpgrades(RPMDepends,Upgrades):       __slots__ = ()
class RPMConflicts(RPMDepends,Conflicts):     __slots__ = ()

class RPMObsoletes(Depends):
    __slots__ = ()

    def matches(self, prv):
        if not isinstance(prv, RPMNameProvides) and type(prv) is not Provides:
            return False
        if self.version and not prv.version:
            return False
        if not self.version and prv.version:
            return True
        selfver, selfarch = splitarch(self.version)
        prvver, prvarch = splitarch(prv.version)
        if prvarch and selfarch:
            selfcolor = getArchColor(selfarch)
            prvcolor = getArchColor(prvarch)
            if selfcolor and prvcolor and selfcolor != prvcolor:
                return False
        return checkdep(prvver, self.relation, selfver)

_SCOREMAP = {}
def getArchScore(arch, _sm=_SCOREMAP):
    if arch not in _sm:
        score = rpm.archscore(arch)
        _sm[arch] = score
    return _sm.get(arch, 0)

# TODO: Embed color into nameprovides and obsoletes relations.
_COLORMAP = {"noarch": 0, "x86_64": 2, "ppc64": 2, "s390x": 2, "sparc64": 2}
def getArchColor(arch, _cm=_COLORMAP):
    return _cm.get(arch, 1)


class SystemProvides(object):

    def __init__(self):
        self._provides = {}
        for attr in ["Sysinfo", "Rpmlib", "Getconf", "Cpuinfo"]:
            try:
                ds = getattr(rpm.ds, attr)()
            except (TypeError, SystemError, AttributeError):
                pass
            else:
                for item in ds:
                    self._provides.setdefault(ds.N(), []).append(ds.EVR())

    def match(self, name, relation=None, version=None):
        prvvers = self._provides.get(name)
        if prvvers is not None:
            if relation is None or version is None:
                return True
            for prvver in prvvers:
                if checkdep(prvver, relation, version):
                    return True
        return False


system_provides = SystemProvides()

def collapse_libc_requires(requires):
    """ optionally collapse libc.so.6 requires into highest requires """
    if sysconf.get("rpm-collapse-libc-requires", True):
        best = None
        for req in requires:
            if (req[1].startswith('libc.so.6') and
                not req[1].startswith('libc.so.6()') and
                (not best or vercmp(req[1], best[1]) > 0)):
                best = req
        requires = [x for x in requires
                   if not x[1].startswith('libc.so.6') or x == best]
    return requires

def enablePsyco(psyco):
    psyco.bind(RPMPackage.equals)
    psyco.bind(RPMPackage.coexists)
    psyco.bind(RPMPackage.matches)
    psyco.bind(RPMPackage.search)
    psyco.bind(RPMPackage.__lt__)
    psyco.bind(RPMDepends.matches)
    psyco.bind(RPMObsoletes.matches)

hooks.register("enable-psyco", enablePsyco)

# vim:ts=4:sw=4:et

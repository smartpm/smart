#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Mauricio Teixeira <mteixeira@webset.net>
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
from smart.backends.rpm.rpmver import splitarch
from smart.cache import PackageInfo, Loader
from smart.backends.rpm.base import *
from smart import *
import posixpath
import locale
import os
from re import sub
from textwrap import wrap


class YaST2PackageInfo(PackageInfo):
    def __init__(self, package, loader, info):
        PackageInfo.__init__(self, package)
        self._loader = loader
        self._info = info

    def getURLs(self):
        version, arch = splitarch(self._package.version)

        # replace last digit with media number as yast does
        baseurl = self._loader._baseurl.rstrip("/");
        if baseurl[-1:] == "1" and not baseurl[-2:-1].isdigit():
            baseurl = baseurl.rstrip("1")
            baseurl += self._info.get("media")

        return [posixpath.join(baseurl, self._loader._datadir, arch,
                               self._info.get("filename"))]

    def getInstalledSize(self):
        return int(self._info.get("instsize"))

    def getSize(self, url):
        return int(self._info.get("size"))
                
    def getSummary(self):
        return self._info.get("summary", "")

    def getDescription(self):
        return self._info.get("description", "")

    def getGroup(self):
        return self._info.get("group", "")

class YaST2Loader(Loader):

    __stateversion__ = Loader.__stateversion__+4

    def __init__(self, baseurl, datadir, pkginfofile, pkgdescfile=None):
        Loader.__init__(self)
        self._baseurl = baseurl
        self._datadir = datadir
        self._pkginfofile = pkginfofile
        self._pkgdescfile = pkgdescfile

    def getInfo(self, pkg):
        return YaST2PackageInfo(pkg, self, pkg.loaders[self])

    def getLoadSteps(self):
        pkgfile = open(self._pkginfofile)
        total = 0
        for line in pkgfile:
            if line.startswith("=Pkg: "):
                total += 1
        pkgfile.close()
        return total

    def getInfoEntity(self, tag):
        data = []
        found = False
        for line in self._pkgentry:
            if line.startswith("+" + tag + ":"):
                found = True
                continue
            elif line.startswith("-" + tag + ":"):
                break
            elif line[:7] in ("rpmlib(", "config("):
                continue
            elif found == True:
                parts = line.split(" ")
                if len(parts) == 1:
                    data.append((line, None, None))
                if len(parts) == 2:
                    print "Error parsing package '%s' (tag '%s'). Possibly corrupted channel file (%s)." % (self.curpkgname, tag, self._channel)
                if len(parts) == 3:
                    data.append((parts[0], parts[1], parts[2]))
        return data

    def stripTags(self, s):
        # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/440481
        # this list is neccesarry because chk() would otherwise not know
        # that intag in stripTags() is ment, and not a new intag variable in chk().
        intag = [False]
        def chk(c):
            if intag[0]:
                intag[0] = (c != '>')
                return False
            elif c == '<':
                intag[0] = True
                return False
            return True
        return ''.join([c for c in s if chk(c)])

    def readPkgSummDesc(self, entryname):
        summary = description = reading_ins = reading_del = ""
        if self._pkgdescfile and self._pkgoffsets.has_key(entryname):
            self._descfile.seek((self._pkgoffsets[entryname] + 1))
            summary = self._descfile.readline()[5:-1]
            description = ""
            while 1:
                line = self._descfile.readline()
                if line.startswith("##--"):
                    break
                if line.startswith("-Ins"):
                    reading_ins = False
                    continue
                if line.startswith("+Ins:") or reading_ins == True:
                    reading_ins = True
                    continue
                if line.startswith("-Del"):
                    reading_del = False
                    continue
                if line.startswith("+Del:") or reading_del == True:
                    reading_del = True
                    continue
                if line.startswith("+Des:") or line.startswith("<!--"):
                   continue
                if not line or line[:-1] == "-Des:": break
                for wline in wrap(line, 76):
                    description = description + "\n" + wline
        description = sub('<li>', '* ', description)
        description = self.stripTags(description)
        # Wrapping the text added an extra lf as the first char
        return summary, description[1:]


    def parseEntry(self):
        Pkg = RPMPackage
        Req = RPMRequires
        Prq = RPMPreRequires
        Prv = RPMProvides
        Con = RPMConflicts
        Obs = RPMObsoletes
        NPrv = RPMNameProvides
        # SUSE fields not yet handled
        # Rec / Sug / Src / Aut / Key

        requires = ()
        provides = ()
        conflicts = ()
        obsoletes = ()

        # avoid parsing errors on undefined fields
        requires = prequire = conflicts = obsoletes = []
        group = summary = description = size = instsize = filename = media = ""

        for line in self._pkgentry:
            kw = line[:4]
            if kw == "=Pkg":
                entryname = line[6:]
                nameparts = entryname.split(" ")

                try:
                    # skip entry if arch is not compatible
                    arch = nameparts[3]
                except IndexError:
                    raise Error("Error loading YaST2 channel info. Possibly " \
                                "corrupted file.\n%s" % self._pkginfofile)
                
                if getArchScore(arch) == 0:
                    return
                name = nameparts[0]
                self.curpkgname = name
                version = nameparts[1]
                release = nameparts[2]
                versionarch = "%s-%s@%s" % \
                               (version, release, arch)
            elif kw == "+Req":
                requires = self.getInfoEntity("Req")
            elif kw == "+Prq":
                prequire = self.getInfoEntity("Prq")
            elif kw == "+Prv":
                provides = self.getInfoEntity("Prv")
            elif kw == "+Con":
                conflicts = self.getInfoEntity("Con")
            elif kw == "+Obs":
                obsoletes = self.getInfoEntity("Obs")
            elif kw == "=Loc":
                locparts = line[6:].split(" ")
                media = locparts[0]
                filename = locparts[1]
            elif kw == "=Siz":
                sizeparts = line[6:].split(" ")
                size = sizeparts[0]
                instsize = sizeparts[1]
            elif kw == "=Grp":
                group = line[6:]
            elif kw == "=Shr":
                shares = line[6:].split()
                for pkgshr in self._packages:
                    shrver, shrarch = splitarch(pkgshr.version)
                    if (pkgshr.name == name and 
                    (shrver == (shares[1]+"-"+shares[2]) and shrarch == shares[3])):
                        shrinfo = self.getInfo(pkgshr)
                        summary = shrinfo.getSummary()
                        description = shrinfo.getDescription()
                        break
        
        if summary == "" and description == "":
            summary, description = self.readPkgSummDesc(entryname)

        info = { "summary"     : summary,
                 "description" : description,
                 "size"        : size,
                 "instsize"    : instsize,
                 "group"       : group,
                 "media"       : media,
                 "filename"    : filename }
                 
        prvdict = {}
        for n, r, v in provides:
            if n == name and v == version + "-" + release:
                prv = (NPrv, n, versionarch)
            else:
                prv = (Prv, n, v)
            prvdict[prv] = True

        reqdict = {}
        for n, r, v in requires:
            if not ((r is None or "=" in r) and (Prv, n, v) in prvdict or
                    system_provides.match(n, r, v)):
                    reqdict[(Req, n, r, v)] = True
        for n, r, v in prequire:
            if not ((r is None or "=" in r) and (Prv, n, v) in prvdict or
                    system_provides.match(n, r, v)):
                    reqdict[(Prq, n, r, v)] = True

        cnfdict = {}
        for n, r, v in conflicts:
            cnfdict[(Con, n, r, v)] = True
                        
        upgdict = {}
        upgdict[(Obs, name, "<", versionarch)] = True
                   
        for n, r, v in obsoletes:
            upg = (Obs, n, r, v)
            upgdict[upg] = True
            cnfdict[upg] = True
                    
        pkg = self.buildPackage((Pkg, name, versionarch),
                                prvdict.keys(), collapse_libc_requires(reqdict.keys()),
                                upgdict.keys(), cnfdict.keys())
                    
        pkg.loaders[self] = info
                    

    def load(self):

        prog = iface.getProgress(self._cache)

        try:
            self._infofile = open(self._pkginfofile)
        except (IOError, OSError), e:
            raise Error, "Error opening package information file. %s", e

        if self._pkgdescfile:
            try:
                self._descfile = open(self._pkgdescfile)
                # populate pointers for lines that matches packages on description file
                self._pkgoffsets = {}
                while 1:
                    line = self._descfile.readline()
                    if not line: break
                    if line[:6] == "=Pkg: ":
                        self._pkgoffsets[line[6:-1]] = self._descfile.tell()
            except (IOError, OSError), e:
                pass

        while 1:
            line = self._infofile.readline()
            if not line: break
            if line == "=Ver: 2.0\n": continue
            # Read a full package entry
            if line[:4] == ("=Pkg"):
                self._pkgentry = []
                self._pkgentry.append(line[:-1])
                while 1:
                    eline = self._infofile.readline()[:-1]
                    if not eline: break
                    if eline[:4] == ("##--"): break
                    self._pkgentry.append(eline)
                # Parse the entry
                self.parseEntry()
                prog.add(1)
                prog.show()

        self._pkgoffsets = {}
        self._infofile.close()
        self._descfile.close()

def enablePsyco(psyco):
        psyco.bind(YaST2Loader.getInfoEntity)
        psyco.bind(YaST2Loader.readPkgSummDesc)
        psyco.bind(YaST2Loader.load)

hooks.register("enable-psyco", enablePsyco)
            

# vim:ts=4:sw=4:et

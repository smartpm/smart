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
from gepeto.const import ENFORCE, OPTIONAL, INSTALL, REMOVE
from gepeto.cache import PreRequires
from gepeto import *

class TopoSorter(object):

    def __init__(self):
        self._successors = {}
        self._predcount = {}

    def reset(self):
        self._successors.clear()
        self._predcount.clear()

    def addElement(self, elem):
        if elem not in self._successors:
            self._successors[elem] = {}
            self._predcount[elem] = 0

    def addSuccessor(self, elem1, elem2, obey=ENFORCE):
        # Check for loops, and break them if optional.
        successors = self._successors
        predcount = self._predcount
        if elem2 in successors[elem1]:
            return
        elem2successors = [elem2]
        breakoptional = []
        while elem2successors:
            elem = elem2successors.pop(0)
            for subelem in successors[elem]:
                if subelem == elem1:
                    if obey is OPTIONAL:
                        return
                    elif (successors[elem][elem1] is OPTIONAL or
                          sysconf.get("force-loop")):
                        breakoptional.append(elem)
                    else:
                        raise Error, "Unbreakable loop between %s and %s!" % \
                                     (str(elem1), str(elem2))
                elem2successors.append(subelem)
        for elem in breakoptional:
            del successors[elem][elem1]
            predcount[elem1] -= 1
        successors[elem1][elem2] = obey
        predcount[elem2] += 1

    def getSorted(self):
        successors = self._successors
        predcount = self._predcount.copy()
        result = [x for x in predcount if predcount[x] == 0]
        queue = result[:]
        while queue:
            elem = queue.pop()
            del predcount[elem]
            for succ in successors[elem]:
                predcount[succ] -= 1
                if predcount[succ] == 0:
                    queue.append(succ)
                    result.append(succ)
        assert not predcount, str(predcount)
        return result

class ChangeSetSorter(TopoSorter):

    def __init__(self, changeset=None):
        TopoSorter.__init__(self)
        if changeset:
            self.setChangeSet(changeset)

    def setChangeSet(self, changeset):
        self.reset()
        for pkg in changeset:
            op = changeset[pkg]
            elem = (pkg, op)
            self.addElement(elem)
            if op is INSTALL:

                # Required packages being installed must go in
                # before this package's installation.
                for req in pkg.requires:
                    if isinstance(req, PreRequires):
                        obey = ENFORCE
                    else:
                        obey = OPTIONAL
                    for prv in req.providedby:
                        for prvpkg in prv.packages:
                            if changeset.get(prvpkg) is INSTALL:
                                pred = (prvpkg, INSTALL)
                                self.addElement(pred)
                                self.addSuccessor(pred, elem, obey)

                # Upgraded packages being removed must go in
                # before this package's installation. Notice that
                # depending on the package manager, these remove
                # entries will probably be ripped out and dealt
                # by the package manager itself.
                upgpkgs = [upgpkg for prv in pkg.provides
                                  for upg in prv.upgradedby
                                  for upgpkg in upg.packages]
                upgpkgs.extend([prvpkg for upg in pkg.upgrades
                                       for prv in upg.providedby
                                       for prvpkg in prv.packages])
                for upgpkg in upgpkgs:
                    if changeset.get(upgpkg) is REMOVE:
                        pred = (prvpkg, REMOVE)
                        self.addElement(pred)
                        self.addSuccessor(pred, elem, OPTIONAL)

                # Conflicted packages being removed must go in
                # before this package's installation.
                cnfpkgs = [prvpkg for cnf in pkg.conflicts
                                  for prv in cnf.providedby
                                  for prvpkg in prv.packages]
                cnfpkgs.extend([cnfpkg for prv in pkg.provides
                                       for cnf in prv.conflictedby
                                       for cnfpkg in cnf.packages])
                for cnfpkg in cnfpkgs:
                    if changeset.get(cnfpkg) is REMOVE:
                        pred = (cnfpkg, REMOVE)
                        self.addElement(pred)
                        self.addSuccessor(pred, elem, ENFORCE)

            else: # REMOVE

                # We only care about relations with removed packages
                # here. Relations with installed packages have already
                # been handled above.
                for prv in pkg.provides:
                    for req in prv.requiredby:
                        for reqpkg in req.packages:
                            if changeset.get(reqpkg) is REMOVE:
                                if isinstance(req, PreRequires):
                                    obey = ENFORCE
                                else:
                                    obey = OPTIONAL
                                pred = (reqpkg, REMOVE)
                                self.addElement(pred)
                                self.addSuccessor(pred, elem, obey)


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
from sets import Set

class LoopError(Error): pass

class ElementGroup(object):

    def __init__(self):
        self._relations = {} # (pred, succ) -> True

    def getRelations(self):
        return self._relations.keys()

    def addPredecessor(self, elem, pred):
        self._relations[(pred, elem)] = True

    def addSuccessor(self, pred, elem):
        self._relations[(pred, elem)] = True

class ElementOrGroup(ElementGroup): pass
class ElementAndGroup(ElementGroup): pass

class ElementSorter(object):

    def __init__(self):
        self._successors = {} # pred -> {(succ, kind): True}
        self._predcount = {}  # succ -> n
        self._groups = {}     # (pred, succ, kind) -> [group, ...]

    def reset(self):
        self._successors.clear()
        self._groups.clear()

    def getLoop(self, elem):
        successors = self._successors
        path = [elem]
        done = {}
        loop = {}
        while path:
            dct = successors.get(path[-1])
            if dct:
                for succ, kind in dct:
                    if succ in loop or succ is elem:
                        loop.update(dict.fromkeys(path, True))
                    elif succ not in done:
                        done[succ] = True
                        path.append(succ)
                        break
                else:
                    path.pop()
            else:
                path.pop()
        return loop

    def getLoops(self):
        successors = self._successors
        predcount = self._predcount
        checked = {}
        loops = []
        for elem in successors:
            if predcount.get(elem) and elem not in checked:
                loop = self.getLoop(elem)
                if loop:
                    loops.append(loop)
                    checked.update(loop)
        return loops

    def getLoopMap(self):
        successors = self._successors
        predcount = self._predcount
        loopmap = {}
        for elem in successors:
            if predcount.get(elem) and elem not in loopmap:
                loop = self.getLoop(elem)
                if loop:
                    for loopelem in loop:
                        loopmap[loopelem] = True
        return loopmap

    def getLoopPaths(self, loop):
        if not loop:
            return []
        elem = iter(loop).next()
        successors = self._successors
        paths = []
        path = [elem]
        done = {}
        while path:
            head = path[-1]
            dct = successors.get(head)
            if dct:
                for succ, kind in dct:
                    if succ in loop:
                        if succ is elem:
                            paths.append(path+[elem])
                        else:
                            headsucc = (head, succ)
                            if headsucc not in done:
                                done[headsucc] = True
                                path.append(succ)
                                break
                else:
                    path.pop()
            else:
                path.pop()
        return paths

    def _breakLoop(self, elem, loopmap, saved):
        result = saved.get(elem)
        if result is not None:
            return result
        saved[elem] = False
        result = True
        dct = self._successors.get(elem)
        if dct:
            for succ, kind in dct.keys():
                if (succ in loopmap and
                    not self._breakRelation(elem, succ, kind,
                                            loopmap, saved)):
                    result = False
        saved[elem] = result
        return result

    def _breakRelation(self, pred, succ, kind, loopmap, saved):
        result = saved.get((pred, succ, kind))
        if result is not None:
            return result
        saved[(pred, succ, kind)] = False
        breakit = False
        result = True

        # Check if it's a group relation, and if we can remove
        # the relation from every group.
        groups = self._groups.get((pred, succ, kind))
        if groups:
            found = False
            for group in groups:
                # We can't remove the relation from an AND group
                # without removing other relations.
                if type(group) is ElementAndGroup:
                    if len(group._relations) != 1:
                        break
                # We can't remove the last element of an OR
                # group either.
                elif len(group._relations) == 1:
                    break
            else:
                breakit = True

        if breakit:
            pass
        elif kind == OPTIONAL:
            breakit = True
        elif self._breakLoop(succ, loopmap, saved):
            pass
        else:
            result = False

        if breakit:
            if groups:
                del self._groups[(pred, succ, kind)]
                for group in groups[:]:
                    if type(group) is ElementAndGroup:
                        # Remove group from all relations.
                        for gpred, gsucc in group._relations:
                            if gpred != pred or gsucc != succ:
                                ggroups = self._groups[(gpred, gsucc, kind)]
                                ggroups.remove(group)
                                if not ggroups:
                                    del self._groups[(gpred, gsucc, kind)]
                                    del self._successors[gpred][(gsucc, kind)]
                                    self._predcount[gsucc] -= 1
                    else:
                        del group._relations[(pred, succ)]

            del self._successors[pred][(succ, kind)]
            self._predcount[succ] -= 1

        saved[(pred, succ, kind)] = result
        return result

    def breakLoops(self):
        successors = self._successors
        predcount = self._predcount
        checked = {}
        saved = {}
        result = True
        for elem in successors:
            if predcount.get(elem) and elem not in checked:
                loop = self.getLoop(elem)
                if loop and not self._breakLoop(elem, loop, saved):
                    checked.update(loop)
                    result = False
        return result

    def addElement(self, elem):
        self._successors[elem] = ()

    def addPredecessor(self, succ, pred, kind=ENFORCE):
        self.addSuccessor(pred, succ, kind)

    def addSuccessor(self, pred, succ, kind=ENFORCE):
        successors = self._successors
        predcount = self._predcount
        if succ not in successors:
            successors[succ] = ()
        if not successors.get(pred):
            successors[pred] = {(succ, kind): True}
        else:
            successors[pred][(succ, kind)] = True
        if succ not in predcount:
            predcount[succ] = 1
        else:
            predcount[succ] += 1
        groups = self._groups.get((pred, succ, kind))
        if groups:
            group = ElementAndGroup()
            group.addPredecessor(succ, pred)
            groups.append(group)

    def addGroup(self, group, kind=ENFORCE):
        successors = self._successors
        predcount = self._predcount
        for pred, succ in group._relations:
            groups = self._groups.get((pred, succ, kind))
            if not groups:
                groups = self._groups[(pred, succ, kind)] = []
                dct = successors.get(pred)
                if dct and (succ, kind) in dct:
                    group = ElementAndGroup()
                    group.addSuccessor(pred, succ)
                    groups.append(group)
            groups.append(group)
            if succ not in successors:
                successors[succ] = ()
            if not successors.get(pred):
                successors[pred] = {(succ, kind): True}
            else:
                successors[pred][(succ, kind)] = True
            if succ not in predcount:
                predcount[succ] = 1
            else:
                predcount[succ] += 1

    def getSorted(self):

        if not self.breakLoops():
            raise LoopError, "Unbreakable loops found while sorting"

        successors = self._successors
        predcount = self._predcount.copy()

        result = [x for x in successors if not predcount.get(x)]

        for elem in result:
            dct = successors.get(elem)
            if dct:
                for succ, kind in dct:
                    left = predcount.get(succ)
                    if left is None:
                        continue
                    if left-1 == 0:
                        del predcount[succ]
                        result.append(succ)
                    else:
                        predcount[succ] -= 1

        if len(result) != len(successors):
            raise Error, "Internal error: there are still loops!"

        return result

class ChangeSetSorter(ElementSorter):

    def __init__(self, changeset=None):
        ElementSorter.__init__(self)
        if changeset:
            self.setChangeSet(changeset)

    def setChangeSet(self, changeset):
        self.reset()
        for pkg in changeset:
            op = changeset[pkg]
            elem = (pkg, op)
            self.addElement(elem)

            # Packages being installed or removed must go in
            # before their dependencies are removed, or after
            # their dependencies are reinstalled.
            for req in pkg.requires:
                group = ElementOrGroup()
                for prv in req.providedby:
                    for prvpkg in prv.packages:
                        if changeset.get(prvpkg) is INSTALL:
                            group.addSuccessor((prvpkg, INSTALL), elem)
                        elif prvpkg.installed:
                            if changeset.get(prvpkg) is not REMOVE:
                                break
                            group.addSuccessor(elem, (prvpkg, REMOVE))
                    else:
                        continue
                    break
                else:
                    relations = group.getRelations()
                    if relations:
                        if isinstance(req, PreRequires):
                            kind = ENFORCE
                        else:
                            kind = OPTIONAL
                        if len(relations) == 1:
                            pred, succ = relations[0]
                            self.addSuccessor(pred, succ, kind)
                        else:
                            self.addGroup(group)

            if op is INSTALL:

                # Upgraded packages being removed must go in
                # before this package's installation. Notice that
                # depending on the package manager, these remove
                # entries will probably be ripped out and dealt
                # by the package manager itself during upgrades.
                upgpkgs = [upgpkg for prv in pkg.provides
                                  for upg in prv.upgradedby
                                  for upgpkg in upg.packages]
                upgpkgs.extend([prvpkg for upg in pkg.upgrades
                                       for prv in upg.providedby
                                       for prvpkg in prv.packages])
                for upgpkg in upgpkgs:
                    if changeset.get(upgpkg) is REMOVE:
                        self.addSuccessor((prvpkg, REMOVE), elem, ENFORCE)

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
                        self.addSuccessor((cnfpkg, REMOVE), elem, ENFORCE)


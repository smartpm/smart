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

class LoopError(Error):

    def __init__(self, loops):
        Error.__init__(self, "Unbreakable loops found while sorting")
        self.loops = loops

class ElementSorter(object):

    def __init__(self):
        self._predecessors = {}
        self._successors = {}

    def reset(self):
        self._predecessors.clear()
        self._successors.clear()

    def _getAllSuccessors(self, elem, set):
        dct = self._successors.get(elem)
        if dct:
            for succ in dct:
                if succ not in set:
                    set.add(succ)
                    self._getAllSuccessors(succ, set)

    def _getAllPredecessors(self, elem, set):
        for pred in self._predecessors[elem]:
            if type(pred) is list:
                for subpred in pred:
                    if subpred not in set:
                        set.add(subpred)
                        self._getAllPredecessors(subpred, set)
            else:
                if pred not in set:
                    set.add(pred)
                    self._getAllPredecessors(pred, set)

    def getAllSuccessors(self, elem):
        set = Set()
        self._getAllSuccessors(elem, set)
        return set

    def getAllPredecessors(self, elem):
        set = Set()
        self._getAllPredecessors(elem, set)
        return set

    def getLoop(self, elem):
        succs = self.getAllSuccessors(elem)
        preds = self.getAllPredecessors(elem)
        return succs.intersection(preds)

    def getLoops(self):
        predecessors = self._predecessors
        checked = Set()
        loops = []
        for elem in predecessors:
            if predecessors[elem] and elem not in checked:
                succs = self.getAllSuccessors(elem)
                preds = self.getAllPredecessors(elem)
                loop = succs.intersection(preds)
                if loop:
                    loops.append(loop)
                    checked.update(loop)
        return loops

    def _getLoopPaths(self, loop, path):
        paths = []
        for succ in self._successors[path[-1]]:
            if succ in loop:
                path.append(succ)
                if succ == path[0]: 
                    paths.append(path[:])
                else:
                    paths.extend(self._getLoopPaths(loop, path))
                path.pop()
        return paths

    def getLoopPaths(self, loop):
        if not loop:
            return []
        return self._getLoopPaths(loop, [iter(loop).next()])

    def _breakLoop(self, elem, loop, saved):
        result = saved.get(elem)
        if result is not None:
            return result
        saved[elem] = False

        predecessors = self._predecessors
        successors = self._successors

        result = True

        dct = successors.get(elem)
        if dct:

            breakoptional = {}

            for succ in dct:

                if succ in loop and succ not in breakoptional:
                    kind = dct[succ]

                    succpreds = predecessors[succ]
                    group = None
                    if elem not in succpreds:
                        # It's part of a group. Find it.
                        for group in succpreds:
                            if type(group) is list and elem in group:
                                break
                        else:
                            raise Error, "Internal error: where's the " \
                                         "predecessor?"

                        # Now, check if any other group element
                        # is not in the loop.
                        found = False
                        for subelem in group:
                            if subelem not in loop:
                                found = True
                                break
                        if found:
                            continue

                    if kind == OPTIONAL:

                        # It's optional. Break it and go on.
                        breakoptional[succ] = True

                    else:

                        if group:
                            # It's part of a group. Check if any other
                            # group element is immediately breakable.
                            for _succ in dct:
                                if (_succ is not succ and
                                    dct[_succ] is OPTIONAL and
                                    _succ in group):
                                    breakoptional[_succ] = True
                                    found = True
                                    break
                            if found:
                                continue

                        if group:
                            # It's part of a group. Check if any other
                            # group element is breakable down the road.
                            # We prefer elements in the loop.
                            found = False
                            for subelem in group:
                                if (subelem in loop and
                                    self._breakLoop(subelem, loop, saved)):
                                    found = True
                                    break
                            else:
                                for subelem in group:
                                    if (subelem not in loop and
                                        self._breakLoop(subelem,
                                                         loop, saved)):
                                        found = True
                                        break
                            if found:
                                continue
                        else:
                            # Try to break succ's loop down the road.
                            if self._breakLoop(succ, loop, saved):
                                continue

                        return False

            if breakoptional:
                for succ in breakoptional:
                    del successors[elem][succ]
                    lst = predecessors[succ]
                    try:
                        lst.remove(elem)
                    except ValueError:
                        for group in lst:
                            if type(group) is list and elem in group:
                                newgroup = group[:]
                                newgroup.remove(elem)
                                lst.remove(group)
                                if newgroup:
                                    lst.append(newgroup)

        saved[elem] = True
        return True

    def breakLoops(self):
        predecessors = self._predecessors
        checked = Set()
        saved = {}
        loops = []
        for elem in predecessors:
            if predecessors[elem] and elem not in checked:
                succs = self.getAllSuccessors(elem)
                preds = self.getAllPredecessors(elem)
                loop = succs.intersection(preds)
                if loop and not self._breakLoop(elem, loop, saved):
                    checked.update(loop)
                    loops.append(loop)
        return loops

    def addElement(self, elem):
        if elem not in self._predecessors:
            self._predecessors[elem] = ()

    def addSuccessor(self, pred, elem, kind=ENFORCE):
        self.addPredecessor(self, elem, pred, kind)

    def addPredecessor(self, elem, pred, kind=ENFORCE):
        predecessors = self._predecessors
        successors = self._successors

        lst = predecessors.get(elem)
        if not lst:
            predecessors[elem] = [pred]
        elif pred not in lst:
            lst.append(pred)

        if type(pred) is list:
            for subpred in pred:
                if subpred not in predecessors:
                    predecessors[subpred] = ()
                    successors[subpred] = {elem: kind}
                else:
                    dct = successors.get(subpred)
                    if not dct:
                        successors[subpred] = {elem: kind}
                    else:
                        if kind is ENFORCE or elem not in dct:
                            dct[elem] = kind
        elif pred not in predecessors:
            predecessors[pred] = ()
            successors[pred] = {elem: kind}
        else:
            dct = successors.get(pred)
            if not dct:
                successors[pred] = {elem: kind}
            else:
                if kind is ENFORCE or elem not in dct:
                    dct[elem] = kind

    def getSorted(self):

        loops = self.breakLoops()
        if loops:
            raise LoopError(loops)

        predecessors = self._predecessors
        successors = self._successors
        result = [x for x in predecessors if not predecessors[x]]
        done = dict.fromkeys(result, True)

        for elem in result:

            dct = successors.get(elem)
            if dct:
                for succ in dct:
                    if succ in done:
                        continue
                    for pred in predecessors[succ]:
                        if type(pred) is list:
                            for subpred in pred:
                                if subpred in done:
                                    break
                            else:
                                break
                            continue
                        elif pred not in done:
                            break
                    else:
                        result.append(succ)
                        done[succ] = True

        if len(result) != len(predecessors):
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
            if op is INSTALL:

                # Required packages being installed must go in
                # before this package's installation.
                for req in pkg.requires:
                    if isinstance(req, PreRequires):
                        kind = ENFORCE
                    else:
                        kind = OPTIONAL
                    pred = []
                    for prv in req.providedby:
                        for prvpkg in prv.packages:
                            if changeset.get(prvpkg) is INSTALL:
                                pred.append((prvpkg, INSTALL))
                            elif (prvpkg.installed and
                                  changeset.get(prvpkg) is not REMOVE):
                                break
                        else:
                            continue
                        break
                    else:
                        if pred:
                            if len(pred) == 1:
                                pred = pred[0]
                            self.addPredecessor(elem, pred, kind)


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
                        self.addPredecessor(elem, pred, OPTIONAL)

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
                        self.addPredecessor(elem, pred, ENFORCE)

            else: # REMOVE

                # We only care about relations with removed packages
                # here. Relations with installed packages have already
                # been handled above.

                # Packages that require some dependency on this
                # package without any alternatives in the system
                # must be removed before it.
                for prv in pkg.provides:
                    for req in prv.requiredby:

                        installed = False
                        for reqprv in req.providedby:
                            for reqprvpkg in reqprv.packages:
                                if (reqprvpkg.installed and
                                    changeset.get(reqprvpkg) is not REMOVE):
                                    installed = True
                                    break
                            else:
                                continue
                            break
                        if installed:
                            break

                        for reqpkg in req.packages:
                            if changeset.get(reqpkg) is REMOVE:
                                if isinstance(req, PreRequires):
                                    kind = ENFORCE
                                else:
                                    kind = OPTIONAL
                                pred = (reqpkg, REMOVE)
                                self.addPredecessor(elem, pred, kind)


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
import os, sys

from smart.const import INSTALL, REMOVE
from smart.cache import PreRequires
from smart import *


if sys.version_info < (2, 4):
    from sets import Set as set

    def sorted(iterable, key=None):
       mylist = list(iterable)[:]
       if key:
           def mycmp(a, b):
               return cmp(key(a), key(b))
           mylist.sort(mycmp)
       else:
           mylist.sort()
       return mylist
    __builtins__['sorted'] = sorted


class DisableError(Error):
    """Raised on a request to break a non-existent or unbreakable relation."""

class EnableError(Error):
    """Raised on a request to enable a non-disabled relation."""


class ElementGroup(object):

    def __init__(self):
        self._relations = set()

    def getRelations(self):
        return self._relations

    def addPredecessor(self, succ, pred):
        self._relations.add((pred, succ))

    def addSuccessor(self, pred, succ):
        self._relations.add((pred, succ))


class ElementSorter(object):

    def __init__(self):
        self._successors = {}  # pred -> set([succ])
        self._priorities = {}  # {(pred, succ): priority}
        self._predcount = {}   # succ -> n
        self._disabled = set() # set([(pred, succ)])
        self._maximum_priority = 0

    def reset(self):
        self._successors.clear()
        self._priorities.clear()
        self._predcount.clear()
        self._disabled.clear()
        self._maximum_priority = 0

    def disableRelation(self, relation):
        """Disable the optional ordering between C{pred} and C{succ}."""
        priority = self._priorities.get(relation)
        if priority is None:
            raise DisableError("Ordering between %r and %r doesn't exist."
                               % relation)
        if relation in self._disabled:
            raise DisableError("Ordering between %r and %r is already disabled."
                               % relation)
        self._disabled.add(relation)

    def enableRelation(self, relation):
        if relation not in self._disabled: # XXX UNTESTED
            raise EnableError("Ordering between %r and %r is not disabled."
                              % relation)
        self._disabled.remove(relation)

    def getPathData(self, start, end,
                    follow_relations=None, maximum_priority=None):
        """Return all elements and relations leading from C{start} to C{end}.

        The result is a tuple where the first item is the set of elements
        which are involved in paths from C{start} to C{end}, and the second
        item is the relations involved in paths from C{start} to C{end}.
        """
        successors = self._successors
        path = [start]
        seen = set()
        elements = set()
        relations = set()
        while path:
            last = path[-1]
            for succ in successors.get(last, ()):
                relation = (last, succ)
                if ((relation not in self._disabled) and
                    (follow_relations is None or
                     relation in follow_relations) and
                    (maximum_priority is None or
                     self._priorities[relation] <= maximum_priority)):
                    if succ in elements or succ == end:
                        path.append(succ)
                        elements.update(path)
                        relpath = []
                        for i in range(len(path)-1):
                            relpath.append((path[i], path[i+1]))
                        relations.update(relpath)
                        path.pop()
                    elif succ not in seen:
                        seen.add(succ)
                        path.append(succ)
                        break
            else:
                path.pop()
        return (elements, relations)

    def getLoops(self):
        """Return all elements and relations participating in loops.

        The result is the same as for L{getPathData()}, except that only
        elements and relations involved in loops will be returned.
        """
        all_loop_elements = set()
        loops = []
        for elem in self._successors:
            if elem not in all_loop_elements:
                loop_elements, loop_relations = self.getPathData(elem, elem)
                if loop_elements:
                    done = set([elem])
                    todo = loop_elements - done
                    while todo:
                        loop_elem = todo.pop()
                        more_elements, more_relations = \
                            self.getPathData(loop_elem, loop_elem)
                        loop_elements.update(more_elements)
                        loop_relations.update(more_relations)
                        done.add(loop_elem)
                        more_elements.difference_update(done)
                        todo.update(more_elements)
                    loops.append((loop_elements, loop_relations))
                    all_loop_elements.update(loop_elements)
        return loops

    def hasLoop(self, elements, relations):
        for elem in elements:
            data = self.getPathData(elem, elem, follow_relations=relations)
            if data[0]:
                return True
        return False

    def countRelationsInLoop(self, elements, relations, maximum_priority=None):
        loop_relations = 0
        loop_elements = set()
        for elem in elements:
            if elem not in loop_elements:
                data = self.getPathData(elem, elem,
                                        follow_relations=relations,
                                        maximum_priority=maximum_priority)
                if data[0]:
                    loop_elements.update(data[0])
                    loop_relations += len(data[1])
        return loop_relations

    def _getReenableOrder(self, elements, relations):
        follow_relations = set(relations)
        sort_key = {}
        for relation in relations:
            # Now we're going to produce the tuple which will be used to
            # sort this specific relation.  If the priority of this relation
            # is 1, and if we disable this relation we'll still have 5 other
            # relations in the loop when considering only relatins of
            # priority 0 in the loop, and also 4 relations when considering
            # 0, 1, and 2, and the maximum priority number for all the
            # relations this sorter knows about is 3, we want a tuple such
            # as (1, -5, 0, -4, -4).
            follow_relations.remove(relation)
            sort_tuple = [self._priorities[relation]]
            for priority in range(self._maximum_priority + 1):
                sort_tuple.append(-self.countRelationsInLoop(elements,
                                                             follow_relations,
                                                             priority))
            sort_key[relation] = tuple(sort_tuple)
            follow_relations.add(relation)
        return sorted(relations, key=sort_key.get)

    def breakLoops(self):
        # Reenable all relations so that we identify all potential
        # loops correctly, and retrieve data for all loops.  Note that
        # with all relations enabled, any given element can only possibly
        # be part of one loop.  If that assumption is broken before loops
        # are computed, the logic below may not work in weird cases.
        self._disabled.clear()
        loops = self.getLoops()

        for loop_elements, loop_relations in loops:
            # Get our best guess of a good ordering to try reenabling
            # relations which are part of this loop later.
            reenable_order = self._getReenableOrder(loop_elements,
                                                    loop_relations)

            for relation in loop_relations:
                # Disable all relations participating in this loop.
                self.disableRelation(relation)

            # Ok, the loop is gone. Now, reenable as many relations as
            # possible, without recreating any loops.  Do that in an
            # order which gives precedence for relations with higher
            # priority, and for relations that are unlikely to
            # recreate big loops.
            for relation in reenable_order:
                if relation in self._disabled:
                    pred, succ = relation
                    elements, relations = \
                        self.getPathData(succ, pred,
                                         follow_relations=loop_relations)
                    if not elements:
                        self.enableRelation(relation)

    def addElement(self, elem):
        if elem not in self._successors:
            self._successors[elem] = set()
            self._predcount[elem] = 0

    def addPredecessor(self, succ, pred, priority=0):
        self.addSuccessor(pred, succ, priority)

    def addSuccessor(self, pred, succ, priority=0):
        pair = pred, succ
        successors = self._successors
        predcount = self._predcount
        if succ not in successors:
            successors[succ] = set()
            predcount[succ] = 0
        if pred not in successors:
            successors[pred] = set([succ])
            predcount[pred] = 0
            predcount[succ] += 1
        elif succ not in successors[pred]:
            successors[pred].add(succ)
            predcount[succ] += 1
        if pair not in self._priorities or self._priorities[pair] > priority:
            self._priorities[pair] = priority
        if priority > self._maximum_priority:
            self._maximum_priority = priority

    def getSorted(self):
        successors = self._successors
        predcount = self._predcount.copy()

        self.breakLoops()

        for pred, succ in self._disabled:
            predcount[succ] -= 1

        result = [x for x in successors if not predcount.get(x)]

        for elem in result:
            for succ in successors.get(elem, ()):
                if (elem, succ) not in self._disabled:
                    left = predcount.get(succ)
                    if left is not None:
                        if left-1 == 0:
                            del predcount[succ]
                            result.append(succ)
                        else:
                            predcount[succ] -= 1

        if len(result) != len(successors):
            raise RuntimeError("There are remaining loops")

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

            relations = []
            def add_relation(pred, succ, priority):
                relations.append((pred, succ, priority))

            for req in pkg.requires:
                if isinstance(req, PreRequires):
                    req_type_priority = 0
                else:
                    req_type_priority = 1
                for prv in req.providedby:
                    for prvpkg in prv.packages:
                        if prvpkg is pkg:
                            continue
                        if changeset.get(prvpkg) is INSTALL:
                            add_relation((prvpkg, INSTALL), elem,
                                         req_type_priority)
                        elif prvpkg.installed:
                            if changeset.get(prvpkg) is not REMOVE:
                                break
                    else:
                        continue
                    break
                else:
                    for args in relations:
                        self.addSuccessor(*args)

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
                    if upgpkg is pkg:
                        continue
                    if changeset.get(upgpkg) is REMOVE:
                        self.addSuccessor((upgpkg, REMOVE), elem)

                # Conflicted packages being removed must go in
                # before this package's installation.
                cnfpkgs = [prvpkg for cnf in pkg.conflicts
                                  for prv in cnf.providedby
                                  for prvpkg in prv.packages
                                   if prvpkg is not pkg]
                cnfpkgs.extend([cnfpkg for prv in pkg.provides
                                       for cnf in prv.conflictedby
                                       for cnfpkg in cnf.packages
                                        if cnfpkg is not pkg])
                for cnfpkg in cnfpkgs:
                    if cnfpkg is pkg:
                        continue
                    if changeset.get(cnfpkg) is REMOVE:
                        self.addSuccessor((cnfpkg, REMOVE), elem)

        assert len(self._successors) == len(changeset)

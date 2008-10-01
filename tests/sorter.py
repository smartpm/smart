import unittest

from smart.sorter import ElementSorter, DisableError


class ElementSorterTest(unittest.TestCase):

    def setUp(self):
        self.sorter = ElementSorter()

    def test_addElement(self):
        self.sorter.addElement(1)
        self.assertEquals(self.sorter.getSorted(), [1])

    def test_disableRelation_fails_with_non_existing_relation(self):
        self.assertRaises(DisableError, self.sorter.disableRelation, (0, 1))

    def test_disableRelation_fails_with_disabled_relation(self):
        self.sorter.addSuccessor(0, 1, priority=1)
        self.sorter.disableRelation((0, 1))
        self.assertRaises(DisableError, self.sorter.disableRelation, (0, 1))

    def test_getPathData_with_one_relation(self):
        self.sorter.addSuccessor(0, 1)
        self.assertEquals(self.sorter.getPathData(0, 1),
                          (set([0, 1]), set([(0, 1)])))

    def test_getPathData_with_multiple_relations_in_loop(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3)
        sorter.addSuccessor(3, 0)
        self.assertEquals(sorter.getPathData(0, 2),
                          (set([0, 1, 2]), set([(0, 1), (1, 2)])))

    def test_getPathData_with_multiple_paths_between_start_and_end(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3)
        sorter.addSuccessor(1, 3)
        self.assertEquals(sorter.getPathData(0, 3),
                          (set([0, 1, 2, 3]),
                           set([(0, 1), (1, 2), (2, 3), (1, 3)])))

    def test_getPathData_with_loop(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 0)
        self.assertEquals(sorter.getPathData(0, 0),
                          (set([0, 1, 2]), set([(0, 1), (1, 2), (2, 0)])))

    def test_getPathData_with_unexisting_path(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3)
        self.assertEquals(sorter.getPathData(3, 0), (set(), set()))

    def test_getPathData_considers_disabled_relations(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3, priority=1)
        sorter.addSuccessor(1, 3)
        self.assertEquals(sorter.getPathData(0, 3),
                          (set([0, 1, 2, 3]),
                           set([(0, 1), (1, 2), (2, 3), (1, 3)])))
        sorter.disableRelation((2, 3))
        self.assertEquals(sorter.getPathData(0, 3),
                          (set([0, 1, 3]), set([(0, 1), (1, 3)])))

    def test_getPathData_with_follow_relations(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3)
        sorter.addSuccessor(1, 3)
        relations = set([(0, 1), (1, 2), (1, 3)])
        self.assertEquals(sorter.getPathData(0, 3, follow_relations=relations),
                          (set([0, 1, 3]), set([(0, 1), (1, 3)])))

    def test_getLoops_without_loops(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3)
        self.assertEquals(sorter.getLoops(), [])

    def test_getLoops(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3)
        sorter.addSuccessor(2, 0)
        self.assertEquals(sorter.getLoops(),
                          [(set([0, 1, 2]), set([(0, 1), (1, 2), (2, 0)]))])

    def test_getLoops_with_two_different_loops_connected(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 0)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3)
        sorter.addSuccessor(3, 2)
        sorter.addSuccessor(3, 4)
        loop1 = (set([0, 1]), set([(0, 1), (1, 0)]))
        loop2 = (set([2, 3]), set([(2, 3), (3, 2)]))
        data = sorter.getLoops()
        self.assertTrue(data in [[loop1, loop2], [loop2, loop1]], data)

    def test_sorting(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3)
        sorter.addSuccessor(2, 4)
        sorter.addSuccessor(3, 4)
        self.assertEquals(sorter.getSorted(), [0, 1, 2, 3, 4])

    def test_loop(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 0)
        sorted = sorter.getSorted()
        # May be broken anywhere.
        self.assertTrue(sorted in ([0, 1, 2], [1, 2, 0], [2, 0, 1]), sorted)

    def test_basic_loop_breaking(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3)
        sorter.addSuccessor(2, 4)
        sorter.addSuccessor(3, 4)
        sorter.addSuccessor(3, 1, priority=1)
        self.assertEquals(sorter.getSorted(), [0, 1, 2, 3, 4])

    def test_basic_loop_breaking_2(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1, priority=1)
        sorter.addSuccessor(1, 2, priority=1)
        sorter.addSuccessor(2, 3, priority=2)
        sorter.addSuccessor(3, 4, priority=1)
        sorter.addSuccessor(4, 0, priority=1)
        self.assertEquals(sorter.getSorted(), [3, 4, 0, 1, 2])

    def test_break_the_least_number_of_relations(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(0, 2)
        sorter.addSuccessor(1, 2)
        sorter.addSuccessor(2, 3)
        sorter.addSuccessor(3, 0)
        sorter.addSuccessor(3, 1)
        self.assertEquals(sorter.getSorted(), [3, 0, 1, 2])

    def test_enable_relations_favoring_higher_priority_relations_first_1(self):
        sorter = self.sorter
        sorter.addSuccessor(0, 1)
        sorter.addSuccessor(0, 2, 1)
        sorter.addSuccessor(1, 2, 1)
        sorter.addSuccessor(2, 3)
        sorter.addSuccessor(3, 0)
        sorter.addSuccessor(3, 1)
        self.assertEquals(sorter.getSorted(), [2, 3, 0, 1])

    def test_enable_relations_favoring_higher_priority_relations_first_1(self):
        sorter = self.sorter
        for i in range(5):
            sorter.addSuccessor(i, i+1)
            sorter.addSuccessor(i+1, i)
        sorter.addSuccessor(0, 5)
        self.assertEquals(sorter.getSorted(), [0, 1, 2, 3, 4, 5])

from tests.mocker import MockerTestCase

from smart.util.distance import globdistance


class DistanceTestBase(MockerTestCase):

    def test_globdistance_with_empty_values(self):
        self.assertEquals(globdistance("", ""), (0, 1.0))
        self.assertEquals(globdistance("", "a"), (1, 0.0))
        self.assertEquals(globdistance("a", ""), (1, 0.0))

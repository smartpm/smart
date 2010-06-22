from mocker import MockerTestCase

from smart.searcher import Searcher


class SearcherTest(MockerTestCase):

    def test_group(self):
        searcher = Searcher()
        searcher.addGroup("foo")

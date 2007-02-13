import unittest
import os


class TestImport(unittest.TestCase):

    def test_import(self):
        """Verify if cElementTree is hacked to work inside Smart."""
        import smart.util
        util_dir = os.path.dirname(smart.util.__file__)
        if os.path.isfile(os.path.join(util_dir, "cElementTree.so")):
            from smart.util.cElementTree import ElementTree

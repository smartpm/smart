from unittest import TestCase

class TestImport(TestCase):

    def test_import(self):
        """Verify if cElementTree is hacked to work inside Smart."""
        from smart.util.cElementTree import ElementTree

import unittest
import os

from smart.uncompress import Uncompressor

from tests import TESTDATADIR

class UncompressorTest(unittest.TestCase):

    def compare_files(self, file1, file2):
        import filecmp
        return filecmp.cmp(file1, file2)

    def tearDown(self):
        path = "%s/uncompress/test" % TESTDATADIR
        if os.path.exists(path): os.unlink(path)

    def uncompress_file(self, file):
        uncompressor = Uncompressor()
        handler = uncompressor.getHandler(file)
        self.assertTrue(handler.query(file))
        path = "%s/uncompress/test" % TESTDATADIR
        self.assertTrue(path == handler.getTargetPath(file))
        uncompressor.uncompress(file)
        orig = "%s/uncompress/test.txt" % TESTDATADIR
        self.assertTrue(self.compare_files(orig, path))
        os.unlink(path)

    def test_gzip(self):
        self.uncompress_file("%s/uncompress/test.gz" % TESTDATADIR)

    def test_bzip2(self):
        self.uncompress_file("%s/uncompress/test.bz2" % TESTDATADIR)

    def test_lzma(self):
        self.uncompress_file("%s/uncompress/test.lzma" % TESTDATADIR)

    def test_xz(self):
        self.uncompress_file("%s/uncompress/test.xz" % TESTDATADIR)

    def test_zip(self):
        self.uncompress_file("%s/uncompress/test.zip" % TESTDATADIR)

    def test_7zip(self):
        self.uncompress_file("%s/uncompress/test.7z" % TESTDATADIR)


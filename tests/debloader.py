from StringIO import StringIO
import unittest

from smart.backends.deb.loader import DebTagLoader, DEBARCH, TagFile
from smart.backends.deb.base import DebBreaks
from smart.cache import Cache


SMARTPM_SECTION = """\
Package: smartpm-core
Status: install ok installed
Priority: optional
Section: admin
Installed-Size: 2116
Architecture: %s
Source: smart
Version: 0.51-1
Description: Summary line
 Full description.
""" % DEBARCH


class FakeLoader(DebTagLoader):

    def __init__(self, sections=[]):
        super(FakeLoader, self).__init__()
        self.fake_sections = sections
        self.fake_built = []

    def getSections(self, prog):
        for offset, section in enumerate(self.fake_sections):
            tf = TagFile(StringIO(section))
            tf.advanceSection()
            yield tf, offset

    def getDict(self, pkg):
        for offset, section in enumerate(self.fake_sections):
            tf = TagFile(StringIO(section))
            tf.advanceSection()
            return tf.copy()

class DebLoaderTest(unittest.TestCase):

    def setUp(self):
        self.cache = Cache()
        self.loader = FakeLoader()
        self.loader.setCache(self.cache)

    def test_right_arch(self):
        self.loader.fake_sections = [SMARTPM_SECTION]
        self.loader.load()
        packages = self.cache.getPackages()
        self.assertEquals(len(packages), 1)
        self.assertEquals(packages[0].name, "smartpm-core")
        self.assertEquals(packages[0].version, "0.51-1")

    def test_wrong_arch(self):
        wrong_arch = ["i386", "amd64"][DEBARCH == "i386"]
        section = SMARTPM_SECTION.replace(DEBARCH, wrong_arch)
        self.loader.fake_sections = [section]
        self.loader.load()
        packages = self.cache.getPackages()
        self.assertEquals(len(packages), 0)

    def test_all_arch(self):
        section = SMARTPM_SECTION.replace(DEBARCH, "all")
        self.loader.fake_sections = [section]
        self.loader.load()
        packages = self.cache.getPackages()
        self.assertEquals(len(packages), 1)
        self.assertEquals(packages[0].name, "smartpm-core")
        self.assertEquals(packages[0].version, "0.51-1")

    def test_breaks(self):
        section = SMARTPM_SECTION + "Breaks: name (= 1.0)"
        self.loader.fake_sections = [section]
        self.loader.load()
        packages = self.cache.getPackages()
        self.assertEquals(len(packages), 1)
        self.assertEquals(len(packages[0].conflicts), 1)
        breaks = packages[0].conflicts[0]
        self.assertEquals(breaks.name, "name")
        self.assertEquals(breaks.relation, "=")
        self.assertEquals(breaks.version, "1.0")
        self.assertEquals(type(breaks), DebBreaks)

    def test_badsize(self):
        section = SMARTPM_SECTION.replace("Installed-Size: 2116\n", \
                                          "Installed-Size: 123M\n")
        self.loader.fake_sections = [section]
        self.loader.load()
        packages = self.cache.getPackages()
        info = self.loader.getInfo(packages[0])
        try:
            self.assertEquals(info.getInstalledSize(), None)
        except ValueError, e:
            self.fail(e)


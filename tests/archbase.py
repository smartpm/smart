import os

from mocker import MockerTestCase

from smart.backends.arch.base import ArchPackage, Package, Provides
from smart.backends.arch.archver import splitarch, splitrelease
from smart import sysconf


class ArchPackageTest(MockerTestCase):

    def test_sorting_name_takes_precedence(self):
        pkg1 = ArchPackage("name1", "3.0-1-i686")
        pkg2 = ArchPackage("name2", "1.0-1-i686")
        pkg3 = ArchPackage("name3", "2.0-1-i686")
        lst = [pkg3, pkg1, pkg2]
        lst.sort()
        self.assertEquals(lst, [pkg1, pkg2, pkg3])

    def test_sorting_version_takes_precedence_over_release(self):
        pkg1 = ArchPackage("name", "1.0-3-i686")
        pkg2 = ArchPackage("name", "2.0-2-i686")
        pkg3 = ArchPackage("name", "3.0-1-i686")
        lst = [pkg3, pkg1, pkg2]
        lst.sort()
        self.assertEquals(lst, [pkg1, pkg2, pkg3])

    def test_sorting_version_takes_precedence_over_arch(self):
        pkg1 = ArchPackage("name", "1.0-1-i686")
        pkg2 = ArchPackage("name", "2.0-1-x86_64")
        pkg3 = ArchPackage("name", "3.0-1-i686")
        lst = [pkg3, pkg1, pkg2]
        lst.sort()
        self.assertEquals(lst, [pkg1, pkg2, pkg3])

class ArchVerSplitTest(MockerTestCase):

    def test_splitarch(self):
        version, arch = splitarch("1.0-1-i686")
        self.assertEquals(version, "1.0-1")
        self.assertEquals(arch, "i686")

    def test_splitrelease(self):
        version, release = splitrelease("1.0-1")
        self.assertEquals(version, "1.0")
        self.assertEquals(release, "1")


import os

import rpm

from .mocker import MockerTestCase

from smart.backends.rpm.base import RPMPackage, Package, Requires, Provides, \
                                    getTS, collapse_libc_requires
from smart.backends.rpm.rpmver import checkver, splitarch, splitrelease
from smart import sysconf


class getTSTest(MockerTestCase):

    def test_wb_rpm_root_path_must_be_absolute(self):
        """
        Somewhat of a weak test.  I haven't managed to make the code
        break when rpm root isn't absolute, so I decided to do a whitebox
        test and verify that at least the fix which is mentioned in
        #307386 is in place.
        """
        current_path = os.getcwd()
        # Using realpath here because if it happens to be a link, the
        # assertion below will fail. (and /tmp is a symlink on Darwin)
        test_path = os.path.realpath(self.makeDir())
        def cleanup():
            os.chdir(current_path)
            sysconf.remove("rpm-root")
        self.addCleanup(cleanup)
        os.chdir(test_path)
        sysconf.set("rpm-root", "relative-rpm-root")
        ts = getTS()
        self.assertEquals(getTS.root, "%s/relative-rpm-root" % test_path)



class RPMPackageTest(MockerTestCase):

    def test_sorting_name_takes_precedence(self):
        pkg1 = RPMPackage(b"name1", b"3.0-1@i386")
        pkg2 = RPMPackage(b"name2", b"1.0-1@i386")
        pkg3 = RPMPackage(b"name3", b"2.0-1@i386")
        lst = [pkg3, pkg1, pkg2]
        lst.sort()
        self.assertEquals(lst, [pkg1, pkg2, pkg3])

    def test_sorting_uses_name_when_different_package_types(self):
        pkg1 = RPMPackage(b"name1", b"3.0-1@i386")
        pkg2 = Package(b"name2", b"1.0-1@i386")
        pkg3 = Package(b"name3", b"2.0-1@i386")
        lst = [pkg3, pkg1, pkg2]
        lst.sort()
        self.assertEquals(lst, [pkg1, pkg2, pkg3])

    def test_sorting_version_takes_precedence_over_arch(self):
        pkg1 = RPMPackage(b"name", b"1.0-1@i386")
        pkg2 = RPMPackage(b"name", b"2.0-1@i686")
        pkg3 = RPMPackage(b"name", b"3.0-1@i386")
        lst = [pkg3, pkg1, pkg2]
        lst.sort()
        self.assertEquals(lst, [pkg1, pkg2, pkg3])

    def test_sorting_arch_used_when_same_version(self):
        pkg1 = RPMPackage(b"name", b"1.0-1@i386")
        pkg2 = RPMPackage(b"name", b"1.0-1@i586")
        pkg3 = RPMPackage(b"name", b"1.0-1@i686")
        lst = [pkg3, pkg1, pkg2]
        lst.sort()
        self.assertEquals(lst, [pkg1, pkg2, pkg3])

    def test_sorting_color_takes_precedence_over_version(self):
        pkg1 = RPMPackage(b"name", b"1.0-1@x86_64")
        pkg2 = RPMPackage(b"name", b"2.0-1@i386")
        pkg3 = RPMPackage(b"name", b"3.0-1@i386")
        lst = [pkg1, pkg2, pkg3]
        lst.sort()
        self.assertEquals(lst, [pkg2, pkg3, pkg1])

    def test_equals_with_provides_with_empty_name_doesnt_fail(self):
        provides1 = Provides(b"", b"1.0")
        provides2 = Provides(b"/foo/bar", b"1.0")
        pkg1 = RPMPackage(b"name", b"1.0")
        pkg2 = RPMPackage(b"name", b"1.0")
        pkg1.provides = [provides1]
        pkg2.provides = [provides1, provides2]
        self.assertTrue(pkg1.equals(pkg2))
        self.assertTrue(pkg2.equals(pkg1))

    def test_collapse_libc_requires(self):
        requires1 = (Requires, b"libc.so.6(GLIBC_2.3.4)(64bit)", None, None)
        requires2 = (Requires, b"libc.so.6(GLIBC_2.2.5)(64bit)", None, None)
        requires3 = (Requires, b"libc.so.6()(64bit)", None, None)
        requires = [requires1, requires2, requires3]
        sysconf.set("rpm-collapse-libc-requires", False)
        req = collapse_libc_requires(requires)
        self.assertEquals(req, requires)
        sysconf.set("rpm-collapse-libc-requires", True)
        req = collapse_libc_requires(requires)
        self.assertEquals(req, [requires1])

class RPMVerCheckTest(MockerTestCase):

    def test_checkstring(self):
        self.assertTrue(checkver(b"1", b"1"))

    def test_checknone(self):
        self.assertTrue(checkver(None, None))

    def test_checkdistepoch(self):
        self.assertTrue(checkver(b"1-2:3", b"1-2"))

class RPMVerSplitTest(MockerTestCase):

    def test_splitarch(self):
        version, arch = splitarch(b"1.0-1@i686")
        self.assertEquals(version, b"1.0-1")
        self.assertEquals(arch, b"i686")

    def test_splitrelease(self):
        version, release = splitrelease(b"1.0-1.fc13")
        self.assertEquals(version, b"1.0")
        self.assertEquals(release, b"1.fc13")

    def test_distepoch(self):
        version, release = splitrelease(b"1.0-1-mdv2011.0")
        self.assertEquals(version, b"1.0")
        self.assertEquals(release, b"1")


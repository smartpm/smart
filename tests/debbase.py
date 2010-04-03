import sys

from tests.mocker import MockerTestCase

from smart.backends.deb.base import getArchitecture
from smart.backends.deb.debver import splitrelease


class GetArchitectureTest(MockerTestCase):

    def fake_uname(self):
        return ('Linux', 'burma', '2.6.24-19-generic',
                '#1 SMP Wed Aug 20 22:56:21 UTC 2008', self.fake_arch)

    def set_arch_and_platform(self, arch, platform):
        self.fake_arch = arch
        sys.platform = platform

    def setUp(self):
        self.fake_arch = "i686"
        self.real_platform = sys.platform

        uname_mock = self.mocker.replace("os.uname")
        uname_mock()
        self.mocker.call(self.fake_uname)
        self.mocker.replay()

    def tearDown(self):
        sys.platform = self.real_platform

    def test_get_architecture_with_i686_linux2(self):
        self.set_arch_and_platform("i686", "linux2")
        self.assertEquals(getArchitecture(), "i386")

    def test_get_architecture_with_i686_anything(self):
        self.set_arch_and_platform("i686", "anything")
        self.assertEquals(getArchitecture(), "anything-i386")

    def test_get_architecture_with_i86pc_anything(self):
        self.set_arch_and_platform("i86pc", "anything")
        self.assertEquals(getArchitecture(), "anything-i386")

    def test_get_architecture_with_i386_darwin(self):
        self.set_arch_and_platform("i386", "darwin")
        self.assertEquals(getArchitecture(), "darwin-i386")
 
    def test_get_architecture_with_i86pc_sunos5(self):
        self.set_arch_and_platform("i86pc", "sunos5")
        self.assertEquals(getArchitecture(), "solaris-i386")

class DebVerSplitTest(MockerTestCase):

    def test_splitrelease(self):
        version, release = splitrelease("1.0-1_0ubuntu0.10.04")
        self.assertEquals(version, "1.0")
        self.assertEquals(release, "1_0ubuntu0.10.04")


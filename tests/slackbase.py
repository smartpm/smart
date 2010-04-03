import os

from mocker import MockerTestCase

from smart.backends.slack.base import SlackPackage, Package, Provides
from smart.backends.slack.slackver import splitarch, splitrelease
from smart import sysconf


class SlackPackageTest(MockerTestCase):

    def test_sorting_name_takes_precedence(self):
        pkg1 = SlackPackage("name1", "3.0-i486-1")
        pkg2 = SlackPackage("name2", "1.0-i486-1")
        pkg3 = SlackPackage("name3", "2.0-i486-1")
        lst = [pkg3, pkg1, pkg2]
        lst.sort()
        self.assertEquals(lst, [pkg1, pkg2, pkg3])

    def test_sorting_version_takes_precedence_over_release(self):
        pkg1 = SlackPackage("name", "1.0-i486-3_slack13.0")
        pkg2 = SlackPackage("name", "2.0-i486-2_slack13.0")
        pkg3 = SlackPackage("name", "3.0-i486-1_slack13.0")
        lst = [pkg3, pkg1, pkg2]
        lst.sort()
        self.assertEquals(lst, [pkg1, pkg2, pkg3])

    def test_sorting_version_takes_precedence_over_arch(self):
        pkg1 = SlackPackage("name", "1.0-i486-1")
        pkg2 = SlackPackage("name", "2.0-x86_64-1")
        pkg3 = SlackPackage("name", "3.0-i486-1")
        lst = [pkg3, pkg1, pkg2]
        lst.sort()
        self.assertEquals(lst, [pkg1, pkg2, pkg3])

class SlackVerSplitTest(MockerTestCase):

    def test_splitarch(self):
        version, arch = splitarch("1.0-i486-1")
        self.assertEquals(version, "1.0-1")
        self.assertEquals(arch, "i486")

    def test_splitrelease(self):
        version, release = splitrelease("1.0-1_slack13.0")
        self.assertEquals(version, "1.0")
        self.assertEquals(release, "1_slack13.0")


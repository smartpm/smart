from StringIO import StringIO
import unittest
import sys

from smart.channel import createChannel
from smart.progress import Progress
from smart.fetcher import Fetcher
from smart.const import NEVER
from smart.cache import Cache
from smart import Error, sysconf

from tests import TESTDATADIR


FINGERPRINT = "2AAC 7928 0FBF 0299 5EB5  60E2 2253 B29A 6664 3A0C"


class AptDebChannelTest(unittest.TestCase):

    def setUp(self):
        self.progress = Progress()
        self.fetcher = Fetcher()
        self.cache = Cache()

        # Disable caching so that things blow up when not found.
        self.fetcher.setCaching(NEVER)

        sysconf.set("deb-arch", "i386")

    def tearDown(self):
        sysconf.remove("deb-arch")

    def check_channel(self, channel):
        self.assertEquals(channel.fetch(self.fetcher, self.progress), True)

        loaders = channel.getLoaders()

        self.assertEquals(len(loaders), 1)

        self.cache.addLoader(loaders[0])

        saved = sys.stdout
        sys.stdout = StringIO()
        try:
            self.cache.load()
        finally:
            sys.stdout = saved

        packages = sorted(self.cache.getPackages())

        self.assertEquals(len(packages), 2)
        self.assertEquals(packages[0].name, "name1")
        self.assertEquals(packages[1].name, "name2")

    def test_fetch_with_component(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "./",
                                 "components": "component"})
        self.check_channel(channel)

    def test_fetch_with_unknown_signature(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "./",
                                 "fingerprint": "NON-EXISTENT-FINGERPRINT",
                                 "keyring": "%s/aptdeb/trusted.gpg" %
                                            TESTDATADIR,
                                 "components": "component"})
        try:
            self.check_channel(channel)
        except Error, error:
            self.assertEquals(str(error),
                              "Channel 'alias' signed with unknown key")
        else:
            self.fail("Fetch worked with a bad signature! :-(")

    def test_fetch_with_unknown_signature_without_fingerprint(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "./",
                                 "keyring": "%s/aptdeb/nonexistent.gpg" %
                                            TESTDATADIR,
                                 "components": "component"})
        try:
            self.check_channel(channel)
        except Error, error:
            self.assertEquals(str(error),
                              "Channel 'alias' signed with unknown key")
        else:
            self.fail("Fetch worked with a bad signature! :-(")

    def test_fetch_with_missing_keyring(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "./",
                                 "fingerprint": "NON-EXISTENT-FINGERPRINT",
                                 "keyring": "/dev/null",
                                 "components": "component"})
        try:
            self.check_channel(channel)
        except Error, error:
            self.assertEquals(str(error),
                              "Channel 'alias' signed with unknown key")
        else:
            self.fail("Fetch worked with a bad signature! :-(")

    def test_fetch_with_good_signature(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "./",
                                 "fingerprint": FINGERPRINT,
                                 "keyring": "%s/aptdeb/trusted.gpg" %
                                            TESTDATADIR,
                                 "components": "component"})
        self.check_channel(channel)

    def test_fetch_with_good_signature_without_fingerprint(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "./",
                                 "keyring": "%s/aptdeb/trusted.gpg" %
                                            TESTDATADIR,
                                 "components": "component"})
        self.check_channel(channel)

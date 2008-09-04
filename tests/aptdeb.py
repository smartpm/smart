from StringIO import StringIO
import unittest

from smart.channel import createChannel
from smart.progress import Progress
from smart.fetcher import Fetcher
from smart.const import NEVER
from smart.cache import Cache
from smart import Error

from tests import TESTDATADIR


class AptDebChannelTest(unittest.TestCase):

    def setUp(self):
        self.progress = Progress()
        self.fetcher = Fetcher()
        self.cache = Cache()

        # Disable caching so that things blow up when not found.
        self.fetcher.setCaching(NEVER)

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

    def test_fetch_with_bad_signature(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "./",
                                 "fingerprint": "NON-EXISTENT-FINGERPRINT",
                                 "components": "component"})
        try:
            self.check_channel(channel)
        except Error, error:
            self.assertEquals(str(error), "Channel 'alias' has bad signature")

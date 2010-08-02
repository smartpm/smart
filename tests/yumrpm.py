from StringIO import StringIO
import __builtin__
import shutil
import sys
import os

from smart.channel import createChannel
from smart.progress import Progress
from smart.fetcher import Fetcher
from smart.const import NEVER, DEBUG
from smart.cache import Cache
from smart import Error, sysconf, iface

from tests.mocker import MockerTestCase
from tests import TESTDATADIR


class YumRpmChannelTest(MockerTestCase):

    def setUp(self):
        self.progress = Progress()
        self.fetcher = Fetcher()
        self.cache = Cache()

        self.download_dir = self.makeDir()
        self.fetcher.setLocalPathPrefix(self.download_dir + "/")

        # Disable caching so that things blow up when not found.
        self.fetcher.setCaching(NEVER)

        # Make sure to trigger old bugs in debug error reporting.
        sysconf.set("log-level", DEBUG)

    def tearDown(self):
        sysconf.remove("log-level")
 
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

    def test_fetch(self):
        channel = createChannel("alias",
                                {"type": "rpm-md",
                                 "baseurl": "file://%s/yumrpm" % TESTDATADIR})
        self.check_channel(channel)

    def test_fetch_with_broken_mirrorlist(self):
        def fail_open(filename, mode='r', bufsize=-1):
             raise IOError("emulating a broken mirrorlist...")
        old_open = __builtin__.open
        __builtin__.open = fail_open
        channel = createChannel("alias",
                                {"type": "rpm-md",
                                 "baseurl": "file://%s/yumrpm" % TESTDATADIR,
                                 "mirrorlist": "file://%s/yumrpm/mirrorlist-broken.txt" % TESTDATADIR})
        try:
            try:
                self.check_channel(channel)
            except AttributeError, error:
                # AttributeError: 'exceptions.IOError' object has no attribute 'split'
                self.fail(error)
            except IOError:
                pass
        finally:
             __builtin__.open = old_open

    def test_fetch_with_broken_metalink(self):
        channel = createChannel("alias",
                                {"type": "rpm-md",
                                 "baseurl": "file://%s/yumrpm" % TESTDATADIR,
                                 "mirrorlist": "file://%s/yumrpm/metalink-broken.xml" % TESTDATADIR})
        try:
             self.check_channel(channel)
        except AttributeError, error:
             # AttributeError: 'ExpatError' object has no attribute 'split'
             self.fail(error)

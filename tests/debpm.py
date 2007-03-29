import unittest
import os

from smart.backends.deb.pm import DebPackageManager
from smart.channel import createChannel
from smart.interface import Interface
from smart.progress import Progress
from smart.fetcher import Fetcher
from smart.cache import Cache
from smart.const import INSTALL, REMOVE
from smart import iface

from tests import TESTDATADIR, ctrl


class DebPackageManagerTest(unittest.TestCase):

    def setUp(self):
        self.channel = createChannel("alias",
                                     {"type": "apt-deb",
                                      "baseurl": "file://%s/deb" % TESTDATADIR,
                                      "distribution": "./"})

        class TestInterface(Interface):
            output = []
            def message(self, level, msg):
                self.output.append((level, msg))
            def showOutput(self, data):
                self.output.append(data)


        self.iface = TestInterface(ctrl)

        self.progress = Progress()
        self.fetcher = Fetcher()
        self.cache = Cache()

        self.old_iface = iface.object

        self.channel.fetch(self.fetcher, self.progress)
        self.loader = self.channel.getLoaders()[0]
        self.cache.addLoader(self.loader)

        iface.object = self.iface

        self.cache.load()

        self.pm = DebPackageManager()

    def tearDown(self):
        iface.object = self.old_iface

    def test_packages_are_there(self):
        self.assertEquals(len(self.cache.getPackages()), 2)

    def test_commit_outputs_to_stdout(self):
        self.assertNotEquals(os.getuid(), 0, "Can't run this test with root.")

        pkg = self.cache.getPackages()[0]
        info = self.loader.getInfo(pkg)

        file_url = info.getURLs()[0]
        self.assertEquals(file_url[:7], "file://")
        file_path = file_url[7:]

        rd, wr = os.pipe()

        orig_stdout = os.dup(1)
        orig_stderr = os.dup(2)

        os.dup2(wr, 1)
        os.dup2(wr, 2)

        try:
            self.pm.commit({pkg: INSTALL}, {pkg: [file_path]})
        finally:
            os.dup2(orig_stdout, 1)
            os.dup2(orig_stderr, 2)

        data = os.read(rd, 32768)

        self.assertTrue("superuser privilege" in data, data)
        self.assertEquals(self.iface.output,
                          [(1, "Sub-process dpkg returned an error code (2)")])

    def test_commit_outputs_to_iface(self):
        self.assertNotEquals(os.getuid(), 0, "Can't run this test with root.")

        pkg = self.cache.getPackages()[0]
        info = self.loader.getInfo(pkg)

        file_url = info.getURLs()[0]
        self.assertEquals(file_url[:7], "file://")
        file_path = file_url[7:]

        old_setting = sysconf.get("pm-iface-output")
        sysconf.set("pm-iface-output", True, soft=True)
        try:
            self.pm.commit({pkg: INSTALL}, {pkg: [file_path]})
        finally:
            sysconf.set("pm-iface-output", old_setting, soft=True)

        self.assertEquals(self.iface.output,
            ["\n[unpack] name1_version1-release1\n"
             "dpkg: requested operation requires superuser privilege\n",
             (1, "Sub-process dpkg returned an error code (2)")])

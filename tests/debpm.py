import unittest
import pickle
import os
import tempfile

from smart.backends.deb.base import \
    DebPackage, DebProvides, DebNameProvides, DebPreRequires, DebRequires, \
    DebOrRequires, DebUpgrades, DebConflicts, DebBreaks
from smart.backends.deb.pm import DebPackageManager, DebSorter, UNPACK, CONFIG
from smart.channel import createChannel
from smart.sysconfig import SysConfig
from smart.interface import Interface
from smart.progress import Progress
from smart.fetcher import Fetcher
from smart.cache import Cache, Loader
from smart.const import INSTALL, REMOVE
from smart import iface, sysconf, cache

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

        self.channel.fetch(self.fetcher, self.progress)
        self.loader = self.channel.getLoaders()[0]
        self.cache.addLoader(self.loader)

        self.old_iface = iface.object
        self.old_sysconf = pickle.dumps(sysconf.object)

        iface.object = self.iface

        self.cache.load()

        self.pm = DebPackageManager()

        # skip test if dpkg is unavailable
        dpkg = sysconf.get("dpkg", "dpkg")
        output = tempfile.TemporaryFile()
        status = self.pm.dpkg([dpkg, "--version"], output)
        if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
            if not hasattr(self, 'skipTest'): # Python < 2.7
                self.skipTest = self.fail # error
            self.skipTest("%s not found" % dpkg)

    def tearDown(self):
        iface.object = self.old_iface
        sysconf.object = pickle.loads(self.old_sysconf)

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

        sysconf.set("pm-iface-output", True, soft=True)

        self.pm.commit({pkg: INSTALL}, {pkg: [file_path]})

        self.assertEquals(self.iface.output,
            ["\n[unpack] name1_version1-release1\n"
             "dpkg: requested operation requires superuser privilege\n",
             (1, "Sub-process dpkg returned an error code (2)")])

    def test_deb_non_interactive(self):
        pkg = self.cache.getPackages()[0]
        info = self.loader.getInfo(pkg)

        file_url = info.getURLs()[0]
        self.assertEquals(file_url[:7], "file://")
        file_path = file_url[7:]

        check_results = []
        def check(argv, output):
            check_results.append(os.environ.get("DEBIAN_FRONTEND"))
            check_results.append(os.environ.get("APT_LISTCHANGES_FRONTEND"))
            check_results.append("--force-confold" in argv)
            return 0

        self.pm.dpkg = check

        sysconf.set("pm-iface-output", True, soft=True)
        sysconf.set("deb-non-interactive", True, soft=True)

        self.pm.commit({pkg: INSTALL}, {pkg: [file_path]})

        # One time for --unpack, one time for --configure.
        self.assertEquals(check_results,
                          ["noninteractive", "none", True,
                           "noninteractive", "none", True])

    def test_deb_non_interactive_false(self):
        pkg = self.cache.getPackages()[0]
        info = self.loader.getInfo(pkg)

        file_url = info.getURLs()[0]
        self.assertEquals(file_url[:7], "file://")
        file_path = file_url[7:]

        check_results = []
        def check(argv, output):
            check_results.append(os.environ.get("DEBIAN_FRONTEND"))
            check_results.append(os.environ.get("APT_LISTCHANGES_FRONTEND"))
            check_results.append("--force-confold" in argv)
            return 0

        self.pm.dpkg = check

        sysconf.set("pm-iface-output", False, soft=True)
        sysconf.set("deb-non-interactive", False, soft=True)

        self.pm.commit({pkg: INSTALL}, {pkg: [file_path]})

        # One time for --unpack, one time for --configure.
        self.assertEquals(check_results,
                          [None, None, False,
                           None, None, False])


class DebSorterTest(unittest.TestCase):
    
    def setUp(self):
        self.packages_to_build = []
        class MyLoader(Loader):
            def load(loader):
                for args in self.packages_to_build:
                    loader.buildPackage(*args)
        self.loader = MyLoader()
        self.cache = Cache()
        self.cache.addLoader(self.loader)

    def build(self, *args):
        map = {cache.Package: [],
               cache.Provides: [],
               cache.Requires: [],
               cache.Upgrades: [],
               cache.Conflicts: []}
        for arg in args:
            for cls, lst in map.iteritems():
                if issubclass(arg[0], cls):
                    lst.append(arg)
                    break
            else:
                raise RuntimeError("%r is unknown" % type(arg[0]))
        self.packages_to_build.append(
                (map[cache.Package][0], map[cache.Provides],
                 map[cache.Requires], map[cache.Upgrades],
                 map[cache.Conflicts]))

    def test_conflicts_order_remove_after_unpack_whenever_possible(self):
        self.build((DebPackage, "a", "1"),
                   (DebNameProvides, "a", "1"))
        self.build((DebPackage, "a", "2"),
                   (DebNameProvides, "a", "2"),
                   (DebUpgrades, "a", "<", "2"),
                   (DebRequires, "b", "=", "1"))
        self.build((DebPackage, "b", "1"),
                   (DebNameProvides, "b", "1"),
                   (DebConflicts, "a", "<", "2"))
        self.cache.load()
        changeset = {}
        for pkg in self.cache.getPackages():
            if pkg.name == "a" and pkg.version == "1":
                a_1 = pkg
            elif pkg.name == "a":
                a_2 = pkg
            else:
                b_1 = pkg

        a_1.installed = True

        changeset[a_1] = REMOVE
        changeset[a_2] = INSTALL
        changeset[b_1] = INSTALL

        sorter = DebSorter(changeset)
        sorted = sorter.getSorted()

        self.assertEquals(sorted,
                          [(a_2, UNPACK), (a_1, REMOVE), (b_1, UNPACK),
                           (b_1, CONFIG), (a_2, CONFIG)])

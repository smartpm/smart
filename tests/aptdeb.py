from StringIO import StringIO
import shutil
import sys
import os

from smart.channel import createChannel
from smart.progress import Progress
from smart.fetcher import Fetcher
from smart.const import NEVER
from smart.cache import Cache
from smart import Error, sysconf, iface

from tests.mocker import MockerTestCase
from tests import TESTDATADIR


FINGERPRINT = "2AAC 7928 0FBF 0299 5EB5  60E2 2253 B29A 6664 3A0C"


class AptDebChannelTest(MockerTestCase):

    def setUp(self):
        self.progress = Progress()
        self.fetcher = Fetcher()
        self.cache = Cache()

        self.download_dir = self.makeDir()
        self.fetcher.setLocalPathPrefix(self.download_dir + "/")

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

    def test_fetch_without_component(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "component-less"})
        self.check_channel(channel)

    def test_fetch_without_component_and_release_file(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/deb" % TESTDATADIR,
                                 "distribution": "./"})
        self.check_channel(channel)

    def test_fetch_without_component_and_release_file_with_keyring(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/deb" % TESTDATADIR,
                                 "distribution": "./",
                                 "keyring": "/dev/null"})
        try:
            self.check_channel(channel)
        except Error, error:
            self.assertEquals(str(error),
                              "Download of Release failed for channel 'alias': "
                              "File not found for validation")
        else:
            self.fail("Fetch worked with a bad signature! :-(")

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

    def test_fetch_without_component_and_with_unknown_signature(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "component-less",
                                 "fingerprint": "NON-EXISTENT-FINGERPRINT",
                                 "keyring": "%s/aptdeb/trusted.gpg" %
                                            TESTDATADIR})
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

    def test_fetch_with_unknown_signature_without_fingerprint_and_compon(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "component-less",
                                 "keyring": "%s/aptdeb/nonexistent.gpg" %
                                            TESTDATADIR})
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

    def test_fetch_with_missing_keyring_without_component(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "component-less",
                                 "fingerprint": "NON-EXISTENT-FINGERPRINT",
                                 "keyring": "/dev/null"})
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

    def test_fetch_with_good_signature_but_no_home(self):
        os.putenv("GNUPGHOME", "/no/such/dir")
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "./",
                                 "fingerprint": FINGERPRINT,
                                 "keyring": "%s/aptdeb/trusted.gpg" %
                                            TESTDATADIR,
                                 "trustdb": "%s/aptdeb/trustdb.gpg" %
                                            TESTDATADIR,
                                 "components": "component"})
        try:
             self.check_channel(channel)
        finally:
             os.unsetenv("GNUPGHOME")

    def test_fetch_with_good_signature_without_component(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "component-less",
                                 "fingerprint": FINGERPRINT,
                                 "keyring": "%s/aptdeb/trusted.gpg" %
                                            TESTDATADIR})
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

    def test_fetch_with_good_signature_without_fingerprint_and_component(self):
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "component-less",
                                 "keyring": "%s/aptdeb/trusted.gpg" %
                                            TESTDATADIR})
        self.check_channel(channel)

    def test_fetch_without_component_with_corrupted_packages_file_size(self):
        repo_dir = self.makeDir()
        shutil.copytree(TESTDATADIR + "/aptdeb", repo_dir + "/aptdeb")
        path = os.path.join(repo_dir, "aptdeb/component-less/Packages.gz")
        file = open(path, "a")
        file.write(" ")
        file.close()
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % repo_dir,
                                 "distribution": "component-less"})
        try:
            self.check_channel(channel)
        except Error, error:
            error_message = "Unexpected size (expected 571, got 572)"
            self.assertTrue(str(error).endswith(error_message), str(error))
        else:
            self.fail("Fetch worked with a bad signature! :-(")

    def test_fetch_without_component_with_corrupted_packages_file_md5(self):
        repo_dir = self.makeDir()
        shutil.copytree(TESTDATADIR + "/aptdeb", repo_dir + "/aptdeb")
        path = os.path.join(repo_dir, "aptdeb/component-less/Packages.gz")
        file = open(path, "r+")
        file.seek(0)
        file.write(" ")
        file.close()
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % repo_dir,
                                 "distribution": "component-less"})
        try:
            self.check_channel(channel)
        except Error, error:
            error_message =  ("Invalid MD5 "
                              "(expected 384ccb05e3f6da02312b6e383b211777,"
                              " got 6a2857275a35bf2b79e480e653431f83)")
            self.assertTrue(str(error).endswith(error_message), str(error))
        else:
            self.fail("Fetch worked with a bad signature! :-(")

    def test_fetch_without_component_with_corrupted_packages_file_md5(self):
        repo_dir = self.makeDir()
        shutil.copytree(TESTDATADIR + "/aptdeb", repo_dir + "/aptdeb")
        path = os.path.join(repo_dir, "aptdeb/component-less/Packages.gz")
        file = open(path, "r+")
        file.seek(0)
        file.write(" ")
        file.close()
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % repo_dir,
                                 "distribution": "component-less"})
        try:
            self.check_channel(channel)
        except Error, error:
            error_message =  ("Invalid MD5 "
                              "(expected 384ccb05e3f6da02312b6e383b211777,"
                              " got 6a2857275a35bf2b79e480e653431f83)")
            self.assertTrue(str(error).endswith(error_message), str(error))
        else:
            self.fail("Fetch worked with a bad signature! :-(")

    def test_fetch_with_corrupted_packages_file_size(self):
        repo_dir = self.makeDir()
        shutil.copytree(TESTDATADIR + "/aptdeb", repo_dir + "/aptdeb")
        path = os.path.join(repo_dir,
                            "aptdeb/dists/component/binary-i386/Packages.gz")
        file = open(path, "r+")
        file.seek(0)
        file.write(" ")
        file.close()
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % repo_dir,
                                 "distribution": "./",
                                 "components": "component",
                                 })
        try:
            self.check_channel(channel)
        except Error, error:
            error_message =  ("Invalid MD5 "
                              "(expected 384ccb05e3f6da02312b6e383b211777,"
                              " got 6a2857275a35bf2b79e480e653431f83)")
            self.assertTrue(str(error).endswith(error_message), str(error))
        else:
            self.fail("Fetch worked with a bad signature! :-(")

    def test_fetch_with_corrupted_packages_file_md5(self):
        repo_dir = self.makeDir()
        shutil.copytree(TESTDATADIR + "/aptdeb", repo_dir + "/aptdeb")
        path = os.path.join(repo_dir,
                            "aptdeb/dists/component/binary-i386/Packages.gz")
        file = open(path, "r+")
        file.seek(0)
        file.write(" ")
        file.close()
        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % repo_dir,
                                 "distribution": "./",
                                 "components": "component",
                                 })
        try:
            self.check_channel(channel)
        except Error, error:
            error_message =  ("Invalid MD5 "
                              "(expected 384ccb05e3f6da02312b6e383b211777,"
                              " got 6a2857275a35bf2b79e480e653431f83)")
            self.assertTrue(str(error).endswith(error_message), str(error))
        else:
            self.fail("Fetch worked with a bad signature! :-(")

    def test_fetch_with_component_missing_in_release_file(self):
        iface_mock = self.mocker.patch(iface.object)
        iface_mock.warning("Component 'non-existent' is not in Release file "
                           "for channel 'alias'")
        self.mocker.replay()

        channel = createChannel("alias",
                                {"type": "apt-deb",
                                 "baseurl": "file://%s/aptdeb" % TESTDATADIR,
                                 "distribution": "./",
                                 "components": "non-existent"})

        self.assertEquals(channel.fetch(self.fetcher, self.progress), True)

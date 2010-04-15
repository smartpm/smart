import os

from smart.plugins.aptchannelsync import syncAptChannels
from smart import sysconf

from tests.mocker import MockerTestCase


SOURCES_LIST_1 = """\
# Random stuff.

deb http://some/url/ distro/name1 comp1 comp2
deb-src http://some/url/ distro/name1 comp1 comp2

# deb http://commented/url/ commented/name comp1 comp2

rpm http://some/url/ distro/name2 comp1 comp2
"""

SOURCES_LIST_2 = """\
deb http://some/url/ distro/name3 comp1 comp2
"""

SOURCES_LIST_3 = """
deb http://some/url/ distro/name1 comp1 comp2
deb-src http://some/url/ distro/name1 comp1 comp2
"""

SOURCES_LIST_4 = """
deb cdrom:[Ubuntu 7.10 _Gutsy Gibbon_ - Release i386 (20071016)]/ gutsy main restricted
"""


class APTChannelSyncTest(MockerTestCase):

    def setUp(self):
        self.apt_dir = self.makeDir()
        self.sources_dir = os.path.join(self.apt_dir, "sources.list.d")
        self.keyring_file = os.path.join(self.apt_dir, "trusted.gpg")
        self.trustdb_file = os.path.join(self.apt_dir, "trustdb.gpg")
        os.mkdir(self.sources_dir)
        sysconf.set("sync-apt-keyring", self.keyring_file)
        sysconf.set("sync-apt-trustdb", self.trustdb_file)

    def tearDown(self):
        sysconf.remove("channels")
        sysconf.remove("sync-apt-keyring")
        sysconf.remove("sync-apt-trustdb")

    def test_sychronize_sources_list(self):
        filename = self.makeFile(SOURCES_LIST_1, dirname=self.apt_dir,
                                 basename="sources.list")
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "aptsync-1cd42dbb12232a2e2582ad0145fd0516":
                              {"distribution": "distro/name1",
                               "type": "apt-deb",
                               "name": "distro/name1 - comp1 comp2",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/"},
                          "aptsync-ca9430daa6beaccf4d4c9aad9e365c26":
                              {"type": "apt-rpm",
                               "name": "distro/name2 - comp1 comp2",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/distro/name2"}
                         })

    def test_synchronize_sources_list_directory(self):
        filename = self.makeFile(SOURCES_LIST_1, dirname=self.apt_dir,
                                 basename="sources.list")
        self.makeFile(SOURCES_LIST_2, dirname=self.sources_dir, suffix=".list")
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "aptsync-1cd42dbb12232a2e2582ad0145fd0516":
                              {"type": "apt-deb",
                               "name": "distro/name1 - comp1 comp2",
                               "distribution": "distro/name1",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/"},
                          "aptsync-ca9430daa6beaccf4d4c9aad9e365c26":
                              {"type": "apt-rpm",
                               "name": "distro/name2 - comp1 comp2",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/distro/name2"},
                          "aptsync-a3ea5e5aa96019e33241318e7f87a3d1":
                              {"type": "apt-deb",
                               "name": "distro/name3 - comp1 comp2",
                               "distribution": "distro/name3",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/"},
                         })

    def test_cleanup_removed_entries(self):
        filename = self.makeFile(SOURCES_LIST_1, dirname=self.apt_dir,
                                 basename="sources.list")
        self.makeFile(SOURCES_LIST_2, dirname=self.sources_dir, suffix=".list")
        syncAptChannels(filename, self.sources_dir)
        filename = self.makeFile(SOURCES_LIST_3, dirname=self.apt_dir,
                                 basename="sources.list")
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "aptsync-1cd42dbb12232a2e2582ad0145fd0516":
                              {"type": "apt-deb",
                               "name": "distro/name1 - comp1 comp2",
                               "distribution": "distro/name1",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/"},
                          "aptsync-a3ea5e5aa96019e33241318e7f87a3d1":
                              {"type": "apt-deb",
                               "name": "distro/name3 - comp1 comp2",
                               "distribution": "distro/name3",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/"},
                         })

    def test_ignore_cdrom_entries(self):
        filename = self.makeFile(SOURCES_LIST_4, dirname=self.apt_dir,
                                 basename="sources.list")
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"), None)

    def test_preserves_unrelated_changes(self):
        filename = self.makeFile(SOURCES_LIST_1, dirname=self.apt_dir,
                                 basename="sources.list")
        syncAptChannels(filename, self.sources_dir)
        channel_key = "aptsync-1cd42dbb12232a2e2582ad0145fd0516"
        sysconf.set(("channels", channel_key, "disabled"), True)
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get(("channels", channel_key)),
                          {"distribution": "distro/name1",
                           "type": "apt-deb",
                           "name": "distro/name1 - comp1 comp2",
                           "components": "comp1 comp2",
                           "baseurl": "http://some/url/",
                           "disabled": True})

    def test_keyring_is_set_when_present(self):
        open(self.keyring_file, "w").close()
        filename = self.makeFile(SOURCES_LIST_2, dirname=self.apt_dir,
                                 basename="sources.list")
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"),
                          {"aptsync-a3ea5e5aa96019e33241318e7f87a3d1":
                              {"type": "apt-deb",
                               "name": "distro/name3 - comp1 comp2",
                               "distribution": "distro/name3",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/",
                               "keyring": self.keyring_file}
                           })

    def test_keyring_isnt_reset_after_being_removed(self):
        open(self.keyring_file, "w").close()
        filename = self.makeFile(SOURCES_LIST_2, dirname=self.apt_dir,
                                 basename="sources.list")
        syncAptChannels(filename, self.sources_dir)
        sysconf.remove(("channels",
                        "aptsync-a3ea5e5aa96019e33241318e7f87a3d1",
                        "keyring"))
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"),
                          {"aptsync-a3ea5e5aa96019e33241318e7f87a3d1":
                              {"type": "apt-deb",
                               "name": "distro/name3 - comp1 comp2",
                               "distribution": "distro/name3",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/"},
                          })

    def test_keyring_isnt_changed_if_modified(self):
        open(self.keyring_file, "w").close()
        filename = self.makeFile(SOURCES_LIST_2, dirname=self.apt_dir,
                                 basename="sources.list")
        syncAptChannels(filename, self.sources_dir)
        sysconf.set(("channels",
                     "aptsync-a3ea5e5aa96019e33241318e7f87a3d1",
                     "keyring"),
                    "/a/different/keyring.gpg")
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"),
                          {"aptsync-a3ea5e5aa96019e33241318e7f87a3d1":
                              {"type": "apt-deb",
                               "name": "distro/name3 - comp1 comp2",
                               "distribution": "distro/name3",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/",
                               "keyring": "/a/different/keyring.gpg"},
                          })

    def test_trustdb_is_set_when_present(self):
        open(self.trustdb_file, "w").close()
        filename = self.makeFile(SOURCES_LIST_2, dirname=self.apt_dir,
                                 basename="sources.list")
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"),
                          {"aptsync-a3ea5e5aa96019e33241318e7f87a3d1":
                              {"type": "apt-deb",
                               "name": "distro/name3 - comp1 comp2",
                               "distribution": "distro/name3",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/",
                               "trustdb": self.trustdb_file}
                           })


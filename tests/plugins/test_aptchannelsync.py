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
        os.mkdir(self.sources_dir)
        sysconf.set("sync-apt-keyring", self.keyring_file)

    def tearDown(self):
        sysconf.remove("channels")
        sysconf.remove("sync-apt-keyring")

    def test_sychronize_sources_list(self):
        filename = self.makeFile(SOURCES_LIST_1, dirname=self.apt_dir,
                                 basename="sources.list")
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "aptsync-7448307d0748a16950338f05e5027cf1":
                              {"distribution": "distro/name1",
                               "type": "apt-deb",
                               "name": "distro/name1 - comp1 comp2",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/"},
                          "aptsync-b15198b11bcb8f717051cb4fc5867522":
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
                          "aptsync-7448307d0748a16950338f05e5027cf1":
                              {"type": "apt-deb",
                               "name": "distro/name1 - comp1 comp2",
                               "distribution": "distro/name1",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/"},
                          "aptsync-b15198b11bcb8f717051cb4fc5867522":
                              {"type": "apt-rpm",
                               "name": "distro/name2 - comp1 comp2",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/distro/name2"},
                          "aptsync-daf183fd6a41da026012b24e2d2904b7":
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
                          "aptsync-7448307d0748a16950338f05e5027cf1":
                              {"type": "apt-deb",
                               "name": "distro/name1 - comp1 comp2",
                               "distribution": "distro/name1",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/"},
                          "aptsync-daf183fd6a41da026012b24e2d2904b7":
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
        channel_key = "aptsync-7448307d0748a16950338f05e5027cf1"
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
                          {"aptsync-daf183fd6a41da026012b24e2d2904b7":
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
                        "aptsync-daf183fd6a41da026012b24e2d2904b7",
                        "keyring"))
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"),
                          {"aptsync-daf183fd6a41da026012b24e2d2904b7":
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
                     "aptsync-daf183fd6a41da026012b24e2d2904b7",
                     "keyring"),
                    "/a/different/keyring.gpg")
        syncAptChannels(filename, self.sources_dir)
        self.assertEquals(sysconf.get("channels"),
                          {"aptsync-daf183fd6a41da026012b24e2d2904b7":
                              {"type": "apt-deb",
                               "name": "distro/name3 - comp1 comp2",
                               "distribution": "distro/name3",
                               "components": "comp1 comp2",
                               "baseurl": "http://some/url/",
                               "keyring": "/a/different/keyring.gpg"},
                          })

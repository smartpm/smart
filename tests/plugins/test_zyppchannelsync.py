import os

from smart.plugins.zyppchannelsync import syncZyppRepos
from smart import sysconf

from tests.mocker import MockerTestCase


OPENSUSE_REPO = """\
[openSUSE-11.0-Oss]
name=
baseurl=http://download.opensuse.org/distribution/11.0/repo/oss/
type=NONE
enabled=0
priority=120
autorefresh=0
gpgcheck=1
keeppackages=0
"""

OPENSUSE_UPDATES_REPO = """\
[openSUSE-11.0-Updates]
name=
baseurl=http://download.opensuse.org/update/11.0/
type=NONE
enabled=0
priority=20
autorefresh=0
gpgcheck=1
keeppackages=0
"""

class ZyppRepoSyncTest(MockerTestCase):

    def setUp(self):
        self.zypp_dir = self.makeDir()
        self.repos_dir = os.path.join(self.zypp_dir, "zypp.repos.d")
        os.mkdir(self.repos_dir)

    def test_synchronize_repos_directory(self):
        self.makeFile(OPENSUSE_REPO, dirname=self.repos_dir, basename="opensuse.repo")
        syncZyppRepos(self.repos_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "zyppsync-openSUSE-11.0-Oss":
                              {"type": "rpm-md",
                               "disabled": True,
                               "name": "",
                               "baseurl": "http://download.opensuse.org/distribution/11.0/repo/oss/"},
                         })


    def test_cleanup_removed_entries(self):
        self.makeFile(OPENSUSE_REPO, dirname=self.repos_dir, basename="opensuse.repo")
        syncZyppRepos(self.repos_dir)
        os.unlink(os.path.join(self.repos_dir, "opensuse.repo"))
        syncZyppRepos(self.repos_dir)
        self.assertEquals(sysconf.get("channels"), None)

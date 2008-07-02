import os

from smart.plugins.yumchannelsync import syncYumRepos
from smart import sysconf

from tests.mocker import MockerTestCase


FEDORA_REPO = """\
[base]
name=Fedora 8 - i386 - Base
#baseurl=http://download.fedora.redhat.com/pub/fedora/linux/releases/8/Everything/i386/os/
baseurl=http://mirrors.kernel.org/fedora/releases/8/Everything/i386/os/
#mirrorlist=http://fedora.redhat.com/download/mirrors/fedora-$releasever
enabled=1
gpgcheck=1
"""

FEDORA_DEBUG_REPO = """\
[debug]
name=Fedora 8 - i386 - Debug
#baseurl=http://download.fedora.redhat.com/pub/fedora/linux/releases/8/Everything/i386/debug/
baseurl=http://mirrors.kernel.org/fedora/releases/8/Everything/i386/debug/
#mirrorlist=http://fedora.redhat.com/download/mirrors/fedora-$releasever
enabled=1
gpgcheck=1
"""

class YumRepoSyncTest(MockerTestCase):

    def setUp(self):
        self.yum_dir = self.makeDir()
        self.repos_dir = os.path.join(self.yum_dir, "yum.repos.d")
        os.mkdir(self.repos_dir)

    def test_synchronize_repos_directory(self):
        self.makeFile(FEDORA_REPO, dirname=self.repos_dir, basename="fedora.repo")
        syncYumRepos(self.repos_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "yumsync-base":
                              {"type": "rpm-md",
                               "enabled": "1",
                               "name": "Fedora 8 - i386 - Base",
                               "baseurl": "http://mirrors.kernel.org/fedora/releases/8/Everything/i386/os/"},
                         })


    def test_cleanup_removed_entries(self):
        self.makeFile(FEDORA_REPO, dirname=self.repos_dir, basename="fedora.repo")
        syncYumRepos(self.repos_dir)
        os.unlink(os.path.join(self.repos_dir, "fedora.repo"))
        self.makeFile(FEDORA_DEBUG_REPO, dirname=self.repos_dir, basename="fedora-debug.repo")
        syncYumRepos(self.repos_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "yumsync-debug":
                              {"type": "rpm-md",
                               "enabled": "1",
                               "name": "Fedora 8 - i386 - Debug",
                               "baseurl": "http://mirrors.kernel.org/fedora/releases/8/Everything/i386/debug/"},
                         })

import os

from smart.plugins.yumchannelsync import syncYumRepos, BASEARCH, RELEASEVER
from smart import sysconf

from tests.mocker import MockerTestCase


FEDORA_BASE_REPO = """\
[base]
name=Fedora 8 - i386 - Base
baseurl=http://mirrors.kernel.org/fedora/releases/8/Everything/i386/os/
enabled=1
gpgcheck=1
"""

FEDORA_DEBUG_REPO = """\
[debug]
name=Fedora 8 - i386 - Debug
baseurl=http://mirrors.kernel.org/fedora/releases/8/Everything/i386/debug/
enabled=0
gpgcheck=1
"""

FEDORA_DYNAMIC_REPO = """\
[fedora]
name=Fedora $releasever - $basearch
failovermethod=priority
#baseurl=http://download.fedora.redhat.com/pub/fedora/linux/releases/$releasever/Everything/$basearch/os/
mirrorlist=http://mirrors.fedoraproject.org/mirrorlist?repo=fedora-$releasever&arch=$basearch
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora file:///etc/pki/rpm-gpg/RPM-GPG-KEY
"""

CENTOS_MEDIA_REPO = """\
[c4-media]
name=CentOS-$releasever - Media
baseurl=file:///media/cdrom/
        file:///media/cdrecorder/
gpgcheck=1
enabled=0
gpgkey=file:///usr/share/doc/centos-release-4/RPM-GPG-KEY-centos4
"""

class YumRepoSyncTest(MockerTestCase):

    def setUp(self):
        self.yum_dir = self.makeDir()
        self.repos_dir = os.path.join(self.yum_dir, "yum.repos.d")
        os.mkdir(self.repos_dir)

    def tearDown(self):
        sysconf.remove("channels")

    def test_synchronize_repos_directory(self):
        self.makeFile(FEDORA_BASE_REPO, dirname=self.repos_dir, basename="fedora-base.repo")
        syncYumRepos(self.repos_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "yumsync-base":
                              {"disabled": False,
                               "type": "rpm-md",
                               "name": "Fedora 8 - i386 - Base",
                               "baseurl": "http://mirrors.kernel.org/fedora/releases/8/Everything/i386/os/"},
                         })


    def test_cleanup_removed_entries(self):
        self.makeFile(FEDORA_BASE_REPO, dirname=self.repos_dir, basename="fedora-base.repo")
        syncYumRepos(self.repos_dir)
        os.unlink(os.path.join(self.repos_dir, "fedora-base.repo"))
        self.makeFile(FEDORA_DEBUG_REPO, dirname=self.repos_dir, basename="fedora-debug.repo")
        syncYumRepos(self.repos_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "yumsync-debug":
                              {"disabled": True,
                               "type": "rpm-md",
                               "name": "Fedora 8 - i386 - Debug",
                               "baseurl": "http://mirrors.kernel.org/fedora/releases/8/Everything/i386/debug/"},
                         })

    def test_synchronize_dynamic_repos(self):
        self.makeFile(FEDORA_DYNAMIC_REPO, dirname=self.repos_dir, basename="fedora.repo")
        syncYumRepos(self.repos_dir)
        self.assertEquals(sysconf.get("channels")["yumsync-fedora"]["name"],
                          "Fedora %s - %s" % (RELEASEVER, BASEARCH))

    def test_synchronize_media_repo(self):
        self.makeFile(CENTOS_MEDIA_REPO, dirname=self.repos_dir, basename="c4-media.repo")
        syncYumRepos(self.repos_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "yumsync-c4-media":
                              {"disabled": True,
                               "type": "rpm-md",
                               "name": "CentOS-%s - Media" % RELEASEVER,
                               "baseurl": "localmedia://"},
                         })


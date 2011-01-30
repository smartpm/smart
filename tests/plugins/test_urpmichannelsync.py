import os

from smart.plugins.urpmichannelsync import syncURPMIChannels
from smart import sysconf

from tests.mocker import MockerTestCase


URPMI_CONFIG_MAIN = """\
{
}

Main ftp://ftp.free.fr/mirrors/ftp.mandriva.com/MandrivaLinux/official/2009.0/i586/media/main/release {
  key-ids: 70771ff3
}

Main\ Updates ftp://ftp.free.fr/mirrors/ftp.mandriva.com/MandrivaLinux/official/2009.0/i586/media/main/updates {
  key-ids: 22458a98
  update
}
"""

URPMI_CONFIG_CDROM = """\
Mandriva\ Linux\ -\ 2009.0\ (Free)\ -\ Installer cdrom://i586/media/main {
  ignore
  key-ids: 70771ff3
}
"""

PRODUCT_ID = """\
vendor=mandriva,distribution=mandriva linux,type=base,version=2010.1,branch=final,arch=x86_64
"""

URPMI_CONFIG_MIRRORLIST = """\
MirrorList http://ftp.sunet.se/pub/Linux/distributions/mandrakelinux/official/2010.1/x86_64 {
  mirrorlist: $MIRRORLIST
}
"""

RELEASE = """\
Mandriva Linux release 2010.1 (Official) for x86_64
"""

URPMI_CONFIG_VARIABLES = """\
Variables http://ftp.sunet.se/pub/Linux/distributions/mandrakelinux/official/2010.1/x86_64 {
  mirrorlist: $RELEASE/$ARCH
}
"""

class UrpmiChannelSyncTest(MockerTestCase):

    def setUp(self):
        self.config_dir = self.makeDir()
        self.urpmi_dir = os.path.join(self.config_dir, "urpmi")
        self.media_dir = os.path.join(self.config_dir, "media")
        os.mkdir(self.urpmi_dir)
        sysconf.remove("channels")

    def tearDown(self):
        sysconf.remove("channels")

    def test_synchronize_config_main(self):
        filename = self.makeFile(URPMI_CONFIG_MAIN, dirname=self.urpmi_dir, basename="urpmi.cfg")
        syncURPMIChannels(filename, self.media_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "urpmisync-Main Updates":
                              {"type": "urpmi",
                               "name": "Main Updates",
                               "baseurl": "ftp://ftp.free.fr/mirrors/ftp.mandriva.com/MandrivaLinux/official/2009.0/i586/media/main/updates",
                               "hdlurl": "media_info/synthesis.hdlist.cz",
                               "disabled": False,
                               "removable": False,
                               "priority": 0},

                          "urpmisync-Main":
                              {"type": "urpmi",
                               "name": "Main",
                               "baseurl": "ftp://ftp.free.fr/mirrors/ftp.mandriva.com/MandrivaLinux/official/2009.0/i586/media/main/release",
                               "hdlurl": "media_info/synthesis.hdlist.cz",
                               "disabled": False,
                               "removable": False,
                               "priority": 0},
                        })

    def test_synchronize_config_cdrom(self):
        filename = self.makeFile(URPMI_CONFIG_CDROM, dirname=self.urpmi_dir, basename="urpmi.cfg")
        syncURPMIChannels(filename, self.media_dir)
        self.assertEquals(sysconf.get("channels"), {
                          "urpmisync-Mandriva Linux - 2009.0 (Free) - Installer":
                              {"type": "urpmi",
                               "name": "Mandriva Linux - 2009.0 (Free) - Installer",
                               "baseurl": "localmedia://i586/media/main",
                               "hdlurl": "media_info/synthesis.hdlist.cz",
                               "disabled": True,
                               "removable": True,
                               "priority": 0},
                        })

    def test_synchronize_config_mirrorlist(self):
        product_id = self.makeFile(PRODUCT_ID, dirname=self.config_dir, basename="product.id")
        sysconf.set("product-id", product_id, soft=True)
        filename = self.makeFile(URPMI_CONFIG_MIRRORLIST, dirname=self.urpmi_dir, basename="urpmi.cfg")
        syncURPMIChannels(filename, self.media_dir)
        self.assertEquals(sysconf.get("channels")["urpmisync-MirrorList"]["mirrorurl"],
                          "http://api.mandriva.com/mirrors/base.2010.1.x86_64.list")

    def test_synchronize_config_variables(self):
        release = self.makeFile(RELEASE, dirname=self.config_dir, basename="release")
        sysconf.set("release", release, soft=True)
        filename = self.makeFile(URPMI_CONFIG_VARIABLES, dirname=self.urpmi_dir, basename="urpmi.cfg")
        syncURPMIChannels(filename, self.media_dir)
        self.assertEquals(sysconf.get("channels")["urpmisync-Variables"]["mirrorurl"],
                          "2010.1/x86_64")

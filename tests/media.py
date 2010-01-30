from smart.media import Media, \
                        discoverAutoMountMedias, \
                        discoverFstabMedias, \
                        discoverHalVolumeMedias, \
                        discoverDeviceKitDisksMedias
from smart import Error
from tempfile import NamedTemporaryFile
import unittest

class MediaTest(unittest.TestCase):

    def test_rootismounted(self):
        try:
            media = Media("/")
        except Error, error:
            self.fail("Error(%s)" % error)
        self.assertTrue(media.isMounted())

    def test_fakeisnotmounted(self):
        try:
            media = Media("/no/such/dir")
        except Error, error:
            self.fail("Error(%s)" % error)
        self.assertFalse(media.isMounted())

class AutoMountTest(unittest.TestCase):

    def setUp(self):
        self.auto_master = NamedTemporaryFile()
        self.auto_misc = NamedTemporaryFile()
        self.auto_net = NamedTemporaryFile()

        self.auto_misc.write(AUTO_MISC)
        self.auto_misc.flush()

        self.auto_net.write(AUTO_NET)
        self.auto_net.flush()

        self.auto_master.write(AUTO_MASTER %
                               (self.auto_misc.name, self.auto_net.name))
        self.auto_master.flush()

    def tearDown(self):
        self.auto_master.close()
        self.auto_misc.close()
        self.auto_net.close()

    def test_parse(self):
        result = discoverAutoMountMedias(self.auto_master.name)
        self.assertEquals(len(result), 2)
        self.assertEquals(result[0].getMountPoint(), "/misc/cdrom1")
        self.assertEquals(result[1].getMountPoint(), "/misc/cdrom2")


class FSTabTest(unittest.TestCase):

    def setUp(self):
        self.file = NamedTemporaryFile()
        self.file.write(FSTAB)
        self.file.flush()

    def tearDown(self):
        self.file.close()

    def test_parse(self):
        result = discoverFstabMedias(self.file.name)
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].getMountPoint(), "/media/cdrom0")


class HALTest(unittest.TestCase):

    def test_dbus(self):
        result = discoverHalVolumeMedias()
        for media in result:
            self.assertTrue(media.isRemovable())
            # TODO: check mountpoint and device ?


class DeviceKitTest(unittest.TestCase):

    def test_devkit(self):
        result = discoverDeviceKitDisksMedias()
        for media in result:
            self.assertTrue(media.isRemovable())
            # TODO: check mountpoint and device ?


AUTO_MASTER = """

# Some comment.
/misc   %s --timeout 60
/net    %s

# Another comment.
+auto.master

"""

AUTO_MISC = """
# Yet another comment.
cdrom1  -fstype=iso9660 :/dev/foobar
cdrom2  :/dev/cdrom

"""

AUTO_NET = """
project  :/something/else
"""

FSTAB = """
# <file system> <mount point>   <type>  <options>       <dump>  <pass>
proc            /proc           proc    defaults        0       0
UUID=d6e954e8-71ca-4c2a-90b4-adb554acb41a / ext3 defaults,errors=remount-ro 0 1
bad line
/dev/hda        /media/cdrom0   udf,iso9660 user,noauto     0       0
"""

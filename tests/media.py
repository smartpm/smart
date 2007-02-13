from smart.media import discoverAutoMountMedias
from tempfile import NamedTemporaryFile
import unittest

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

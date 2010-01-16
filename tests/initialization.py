import pickle
import sys

from tests.mocker import MockerTestCase

from smart import initPlugins, sysconf


class InitPluginsTest(MockerTestCase):

    def setUp(self):
        from smart import const
        self.old_sysconf = pickle.dumps(sysconf.object)
        self.old_plugins_dir = const.PLUGINSDIR
        self.plugins_dir = self.makeDir()
        const.PLUGINSDIR = self.plugins_dir

    def tearDown(self):
        from smart import const
        const.PLUGINSDIR = self.old_plugins_dir
        sysconf.object = pickle.loads(self.old_sysconf)

    def test_plugins_dir_is_used(self):
        self.makeFile("import sys; sys.test_worked = True",
                      basename="plugin.py", dirname=self.plugins_dir)
        initPlugins()
        self.assertEquals(getattr(sys, "test_worked", False), True)
        del sys.test_worked


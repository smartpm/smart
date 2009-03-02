import sys

from tests.mocker import MockerTestCase

from smart import initPlugins


class InitPluginsTest(MockerTestCase):

    def setUp(self):
        from smart import const
        self.old_plugins_dir = const.PLUGINSDIR
        self.plugins_dir = self.makeDir()
        const.PLUGINSDIR = self.plugins_dir

    def tearDown(self):
        from smart import const
        const.PLUGINSDIR = self.old_plugins_dir

    def test_plugins_dir_is_used(self):
        self.makeFile("import sys; sys.test_worked = True",
                      basename="plugin.py", dirname=self.plugins_dir)
        initPlugins()
        self.assertEquals(getattr(sys, "test_worked", False), True)
        del sys.test_worked


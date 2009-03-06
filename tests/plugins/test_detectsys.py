import pickle
import sys
import os

from smart.plugins.aptchannelsync import syncAptChannels
from smart import sysconf

from tests.mocker import MockerTestCase


class DetectSysPluginTest(MockerTestCase):

    def setUp(self):
        self.rpm_root = self.makeDir()
        self.deb_root = self.makeDir()
        self.slack_root = self.makeDir()

        sysconf.set("rpm-root", self.rpm_root)
        sysconf.set("deb-root", self.deb_root)
        sysconf.set("slack-root", self.slack_root)

        self.old_sysconf = pickle.dumps(sysconf.object)

    def tearDown(self):
        sysconf.object = pickle.loads(self.old_sysconf)

    def make_rpm(self):
        os.makedirs(os.path.join(self.rpm_root, "var/lib/rpm"))

    def make_deb(self):
        os.makedirs(os.path.join(self.deb_root, "var/lib/dpkg"))

    def make_slack(self):
        os.makedirs(os.path.join(self.slack_root, "var/log/packages"))

    def rerun_plugin(self):
        sys.modules.pop("smart.plugins.detectsys", None)
        import smart.plugins.detectsys

    def test_nothing_detected(self):
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"), None)

    def test_rpm_database_detected(self):
        self.make_rpm()
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"),
                          {"rpm-sys":
                           {"type": "rpm-sys", "name": "RPM System"}})

    def test_rpm_database_detected_with_individual_setting(self):
        self.make_rpm()
        self.make_deb()
        sysconf.set("detect-sys-channels", "rpm")
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"),
                          {"rpm-sys":
                           {"type": "rpm-sys", "name": "RPM System"}})

    def test_deb_database_detected(self):
        self.make_deb()
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"),
                          {"deb-sys":
                           {"type": "deb-sys", "name": "DEB System"}})

    def test_deb_database_detected_with_individual_setting(self):
        self.make_rpm()
        self.make_deb()
        sysconf.set("detect-sys-channels", "deb")
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"),
                          {"deb-sys":
                           {"type": "deb-sys", "name": "DEB System"}})

    def test_slack_database_detected(self):
        self.make_slack()
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"),
                          {"slack-sys":
                           {"type": "slack-sys", "name": "Slackware System"}})

    def test_slack_database_detected_with_individual_setting(self):
        self.make_rpm()
        self.make_slack()
        sysconf.set("detect-sys-channels", "slack")
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"),
                          {"slack-sys":
                           {"type": "slack-sys", "name": "Slackware System"}})

    def test_detect_all(self):
        self.make_rpm()
        self.make_deb()
        self.make_slack()
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"),
                          {"rpm-sys":
                           {"type": "rpm-sys", "name": "RPM System"},
                           "deb-sys":
                           {"type": "deb-sys", "name": "DEB System"},
                           "slack-sys":
                           {"type": "slack-sys", "name": "Slackware System"}})

    def test_detect_all_explicitly_enabled(self):
        self.make_rpm()
        self.make_deb()
        self.make_slack()
        sysconf.set("detect-sys-channels", "rpm,deb,slack")
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"),
                          {"rpm-sys":
                           {"type": "rpm-sys", "name": "RPM System"},
                           "deb-sys":
                           {"type": "deb-sys", "name": "DEB System"},
                           "slack-sys":
                           {"type": "slack-sys", "name": "Slackware System"}})

    def test_detect_all_explicitly_enabled_with_true(self):
        self.make_rpm()
        self.make_deb()
        self.make_slack()
        sysconf.set("detect-sys-channels", True)
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"),
                          {"rpm-sys":
                           {"type": "rpm-sys", "name": "RPM System"},
                           "deb-sys":
                           {"type": "deb-sys", "name": "DEB System"},
                           "slack-sys":
                           {"type": "slack-sys", "name": "Slackware System"}})

    def test_detect_none_when_disabled(self):
        self.make_rpm()
        self.make_deb()
        self.make_slack()
        sysconf.set("detect-sys-channels", "unknown")
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"), None)

    def test_detect_none_when_disabled_with_false(self):
        self.make_rpm()
        self.make_deb()
        self.make_slack()
        sysconf.set("detect-sys-channels", False)
        self.rerun_plugin()
        self.assertEquals(sysconf.get("channels"), None)

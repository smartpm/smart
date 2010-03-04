from smart.backends.slack.loader import SlackLoader, SlackPackageInfo, \
                                        parsePackageInfo
from smart.cache import Cache, Package

from tests.mocker import MockerTestCase


OLD_PACKAGE = """\
PACKAGE NAME: name1-version1-arch1-release1
"""

NEW_PACKAGE = """\
PACKAGE NAME: name2-version2-arch2-release2_slack13.0.txz
"""

class SlackLoaderTest(MockerTestCase):

    def setUp(self):
        self.cache = Cache()
        self.loader = SlackLoader()
        self.loader.setCache(self.cache)

    def test_basic_name(self):
        file = self.makeFile(OLD_PACKAGE)
        info = parsePackageInfo(file)[0]
        self.assertEquals(info['name'], "name1")
        self.assertEquals(info['version'], "version1-arch1-release1")

    def test_fancy_name(self):
        file = self.makeFile(NEW_PACKAGE)
        info = parsePackageInfo(file)[0]
        self.assertEquals(info['name'], "name2")
        self.assertEquals(info['version'], "version2-arch2-release2_slack13.0")
        self.assertEquals(info['type'], ".txz")

    def test_keep_location_with_baseurl(self):
        baseurl = "http://www.example.com/"
        location = "example/path"
        pkg = Package('n', 'v-a-r')
        info = SlackPackageInfo(pkg, {'baseurl':baseurl, 'location':location,
                                      'name':pkg.name, 'version':pkg.version })
        url = info.getURLs()[0]
        self.assertEquals(url, "http://www.example.com/example/path/n-v-a-r.tgz")

    def test_strip_location_from_baseurl(self):
        baseurl = "http://www.example.com/example/"
        location = "./example/path"
        pkg = Package('n', 'v-a-r')
        info = SlackPackageInfo(pkg, {'baseurl':baseurl, 'location':location,
                                      'name':pkg.name, 'version':pkg.version })
        url = info.getURLs()[0]
        self.assertEquals(url, "http://www.example.com/example/path/n-v-a-r.tgz")

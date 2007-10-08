# -*- encoding: utf-8 -*-
from unittest import TestCase

import rpm

import pmock

from smart.backends.rpm.header import RPMHeaderPackageInfo
from smart.backends.rpm.yast2 import YaST2PackageInfo


class RPMHeaderPackageInfoTest(pmock.MockTestCase):

    def test_getSummary_without_header(self):
        package = self.mock()
        loader = self.mock()
        loader.expects(pmock.once()) \
              .getHeader(pmock.eq(package)) \
              .will(pmock.return_value(None))
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getSummary(), u"")

    def test_getDescription_without_header(self):
        package = self.mock()
        loader = self.mock()
        loader.expects(pmock.once()) \
              .getHeader(pmock.eq(package)) \
              .will(pmock.return_value(None))
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getDescription(), u"")

    def test_getSummary_without_tag(self):
        package = self.mock()
        loader = self.mock()
        loader.expects(pmock.once()) \
              .getHeader(pmock.eq(package)) \
              .will(pmock.return_value({}))
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getSummary(), u"")

    def test_getDescription_without_tag(self):
        package = self.mock()
        loader = self.mock()
        loader.expects(pmock.once()) \
              .getHeader(pmock.eq(package)) \
              .will(pmock.return_value({}))
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getDescription(), u"")

    def test_getSummary_decodes_string(self):
        package = self.mock()
        loader = self.mock()
        loader.expects(pmock.once()) \
              .getHeader(pmock.eq(package)) \
              .will(pmock.return_value({rpm.RPMTAG_SUMMARY: "áéíóú"}))
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getSummary(), u"áéíóú")

    def test_getDescription_decodes_string(self):
        package = self.mock()
        loader = self.mock()
        loader.expects(pmock.once()) \
              .getHeader(pmock.eq(package)) \
              .will(pmock.return_value({rpm.RPMTAG_DESCRIPTION: "áéíóú"}))
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getDescription(), u"áéíóú")


class YAST2PackageInfoTest(pmock.MockTestCase):

    def test_getURLs_with_media_replacing(self):
        package = self.mock()
        package.expects_property(pmock.once()) \
               .version().will(pmock.return_value("1.0-1@arch"))
        loader = self.mock()
        loader.expects_property(pmock.once()) \
              ._datadir().will(pmock.return_value("datadir"))
        loader.expects_property(pmock.once()) \
              ._baseurl().will(pmock.return_value("http://baseurl1/"))
        info = YaST2PackageInfo(package, loader,
                                {"media": "7", "filename": "fname"})
        self.assertEquals(info.getURLs(),
                          [u"http://baseurl7/datadir/arch/fname"])

    def test_getURLs_without_media_replacing(self):
        package = self.mock()
        package.expects_property(pmock.once()) \
               .version().will(pmock.return_value("1.0-1@arch"))
        loader = self.mock()
        loader.expects_property(pmock.once()) \
              ._datadir().will(pmock.return_value("datadir"))
        loader.expects_property(pmock.once()) \
              ._baseurl().will(pmock.return_value("http://baseurl11/"))
        info = YaST2PackageInfo(package, loader,
                                {"media": "7", "filename": "fname"})
        self.assertEquals(info.getURLs(),
                          [u"http://baseurl11/datadir/arch/fname"])


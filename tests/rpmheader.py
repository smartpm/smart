# -*- encoding: utf-8 -*-
from unittest import TestCase

import rpm

import pmock

from smart.backends.rpm.header import RPMHeaderPackageInfo


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

# -*- encoding: utf-8 -*-
from unittest import TestCase

import rpm

from mocker import MockerTestCase, expect

from smart.backends.rpm.header import RPMHeaderPackageInfo
from smart.backends.rpm.yast2 import YaST2PackageInfo


class RPMHeaderPackageInfoTest(MockerTestCase):

    def test_getSummary_without_header(self):
        package = self.mocker.mock()
        loader = self.mocker.mock()
        loader.getHeader(package)
        self.mocker.replay()
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getSummary(), u"")

    def test_getDescription_without_header(self):
        package = self.mocker.mock()
        loader = self.mocker.mock()
        loader.getHeader(package)
        self.mocker.replay()
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getDescription(), u"")

    def test_getSummary_without_tag(self):
        package = self.mocker.mock()
        loader = self.mocker.mock()
        loader.getHeader(package)
        self.mocker.result({})
        self.mocker.replay()
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getSummary(), u"")

    def test_getDescription_without_tag(self):
        package = self.mocker.mock()
        loader = self.mocker.mock()
        loader.getHeader(package)
        self.mocker.result({})
        self.mocker.replay()
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getDescription(), u"")

    def test_getSummary_decodes_string(self):
        package = self.mocker.mock()
        loader = self.mocker.mock()
        loader.getHeader(package)
        self.mocker.result({rpm.RPMTAG_SUMMARY: "áéíóú"})
        self.mocker.replay()
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getSummary(), u"áéíóú")

    def test_getDescription_decodes_string(self):
        package = self.mocker.mock()
        loader = self.mocker.mock()
        loader.getHeader(package)
        self.mocker.result({rpm.RPMTAG_DESCRIPTION: "áéíóú"})
        self.mocker.replay()
        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getDescription(), u"áéíóú")


class YAST2PackageInfoTest(MockerTestCase):

    def test_getURLs_with_media_replacing(self):
        package = self.mocker.mock()
        loader = self.mocker.mock()
        expect(package.version).result("1.0-1@arch")
        expect(loader._datadir).result("datadir")
        expect(loader._baseurl).result("http://baseurl1/")
        self.mocker.replay()
        info = YaST2PackageInfo(package, loader,
                                {"media": "7", "filename": "fname"})
        self.assertEquals(info.getURLs(),
                          [u"http://baseurl7/datadir/arch/fname"])

    def test_getURLs_without_media_replacing(self):
        package = self.mocker.mock()
        loader = self.mocker.mock()
        expect(package.version).result("1.0-1@arch")
        expect(loader._datadir).result("datadir")
        expect(loader._baseurl).result("http://baseurl11/")
        self.mocker.replay()
        info = YaST2PackageInfo(package, loader,
                                {"media": "7", "filename": "fname"})
        self.assertEquals(info.getURLs(),
                          [u"http://baseurl11/datadir/arch/fname"])


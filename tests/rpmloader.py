# -*- encoding: utf-8 -*-
from unittest import TestCase

import rpm

from mocker import MockerTestCase, expect, ANY

from smart.backends.rpm.header import \
    RPMHeaderPackageInfo, get_header_filenames, \
    RPMDirLoader, RPMHeaderListLoader
from smart.backends.rpm.yast2 import YaST2PackageInfo
from smart.searcher import Searcher
from smart.cache import Cache

from tests import TESTDATADIR


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


class HeaderFilenamesTest(MockerTestCase):

    def test_header_with_old_filenames(self):
        header = {rpm.RPMTAG_OLDFILENAMES: ["/foo"]}
        self.assertEquals(get_header_filenames(header), ["/foo"])

    def test_header_with_old_filenames_with_one_element(self):
        header = {rpm.RPMTAG_OLDFILENAMES: "/foo"}
        self.assertEquals(get_header_filenames(header), ["/foo"])

    def test_header_with_index(self):
        header = {rpm.RPMTAG_OLDFILENAMES: [],
                  rpm.RPMTAG_BASENAMES: ["foo", "bar", "baz"],
                  rpm.RPMTAG_DIRINDEXES: [0, 1, 0],
                  rpm.RPMTAG_DIRNAMES: ["/dir1/", "/dir2/"]}
        self.assertEquals(get_header_filenames(header),
                          ["/dir1/foo", "/dir2/bar", "/dir1/baz"])

    def test_header_with_index_containing_one_entry(self):
        header = {rpm.RPMTAG_OLDFILENAMES: [],
                  rpm.RPMTAG_BASENAMES: "foo",
                  rpm.RPMTAG_DIRINDEXES: 0,
                  rpm.RPMTAG_DIRNAMES: "/dir/"}
        self.assertEquals(get_header_filenames(header), ["/dir/foo"])

    def test_RPMHeaderPackageInfo_getPathList(self):
        """
        Ensure getPathList is working correctly with indexes.
        """
        header = {rpm.RPMTAG_OLDFILENAMES: [],
                  rpm.RPMTAG_BASENAMES: "foo",
                  rpm.RPMTAG_DIRINDEXES: 0,
                  rpm.RPMTAG_DIRNAMES: "/dir/",
                  rpm.RPMTAG_FILEMODES: 0644}

        package = self.mocker.mock()
        loader = self.mocker.mock()
        loader.getHeader(package)
        self.mocker.result(header)

        # Just assert it's called at all.
        mock_func = self.mocker.replace(get_header_filenames)
        mock_func(header)
        self.mocker.passthrough()

        self.mocker.replay()

        info = RPMHeaderPackageInfo(package, loader)
        self.assertEquals(info.getPathList(), ["/dir/foo"])

    def test_RPMHeaderListLoader_searcher(self):
        """
        Ensure getPathList is working correctly with indexes.
        """
        # Just assert it's called at all.
        get_header_filenames_mock = self.mocker.replace(get_header_filenames)
        get_header_filenames_mock(ANY)
        self.mocker.passthrough()

        self.mocker.replay()

        searcher = Searcher()
        searcher.addPath("/tmp/file1")

        cache = Cache()

        loader = RPMDirLoader(TESTDATADIR + "/rpm",
                              "name1-version1-release1.noarch.rpm")
        loader.setCache(cache)
        loader.load()
        loader.search(searcher)

        results = searcher.getResults()

        self.assertEquals(len(results), 1)
        self.assertEquals(results[0][0], 1.0)
        self.assertEquals(results[0][1].name, "name1")

    def test_RPMHeaderListLoader_loadFileProvides(self):
        get_header_filenames_mock = self.mocker.replace(get_header_filenames)
        get_header_filenames_mock(ANY)
        self.mocker.passthrough()
        self.mocker.count(2)

        self.mocker.replay()

        cache = Cache()

        loader = RPMHeaderListLoader("%s/aptrpm/base/pkglist.main" %
                                     TESTDATADIR, "http://base.url")
        loader.setCache(cache)
        loader.load()

        loader.loadFileProvides("/")

    def test_RPMDirLoader_loadFileProvides(self):
        returned_filenames = []
        def result_callback(filenames):
            returned_filenames.extend(filenames)
        get_header_filenames_mock = self.mocker.replace(get_header_filenames)
        get_header_filenames_mock(ANY)
        self.mocker.passthrough(result_callback)

        self.mocker.replay()

        cache = Cache()

        loader = RPMDirLoader(TESTDATADIR + "/rpm",
                              "name1-version1-release1.noarch.rpm")
        loader.setCache(cache)
        loader.load()

        loader.loadFileProvides({"/tmp/file1": "/tmp/file1"})

        self.assertEquals(returned_filenames, ["/tmp/file1"])

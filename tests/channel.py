import unittest

from smart.channel import parseChannelsDescription, PackageChannel
from smart.cache import Loader


class ParseChannelsDescriptionTest(unittest.TestCase):

    def test_parseChannelsDescription(self):
        data = parseChannelsDescription("""
        [alias]
        type = deb-sys
        name = first = second
        """)
        self.assertEquals(data, {'alias': {'type': 'deb-sys',
                                           'name': 'first = second'}})

    def test_removeLoaders_without_cache(self):
        class TestChannel(PackageChannel):
            def fetch(self, fetcher, progress):
                self._loaders.append(Loader())
        channel = TestChannel("type", "alias")
        channel.fetch(None, None)
        channel.removeLoaders()
        self.assertEquals(channel.getLoaders(), [])

import unittest

from smart.channel import parseChannelsDescription


class ParseChannelsDescriptionTest(unittest.TestCase):

    def test_parseChannelsDescription(self):
        data = parseChannelsDescription("""
        [alias]
        type = deb-sys
        name = first = second
        """)
        self.assertEquals(data, {'alias': {'type': 'deb-sys',
                                           'name': 'first = second'}})

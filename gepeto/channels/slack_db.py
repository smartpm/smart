#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
#
# This file is part of Gepeto.
#
# Gepeto is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gepeto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gepeto; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from gepeto.backends.slack.loader import SlackDBLoader
from gepeto.util.strtools import strToBool
from gepeto.channel import Channel

class SlackDBChannel(Channel):

    def __init__(self, *args):
        Channel.__init__(self, *args)
        self._loadorder = 500

    def fetch(self, fetcher, progress):
        self._loader = SlackDBLoader()
        self._loader.setChannel(self)

def create(type, alias, data):
    name = None
    description = None
    priority = 0
    manual = False
    if isinstance(data, dict):
        name = data.get("name")
        description = data.get("description")
        priority = data.get("priority", 0)
        manual = strToBool(data.get("manual", False))
    elif getattr(data, "tag", None) == "channel":
        for n in data.getchildren():
            if n.tag == "name":
                name = n.text
            elif n.tag == "description":
                description = n.text
            elif n.tag == "priority":
                priority = n.text
            elif n.tag == "manual":
                manual = strToBool(n.text)
    else:
        raise ChannelDataError
    try:
        priority = int(priority)
    except ValueError:
        raise Error, "Invalid priority"
    return SlackDBChannel(type, alias, name, description, priority, manual)

# vim:ts=4:sw=4:et

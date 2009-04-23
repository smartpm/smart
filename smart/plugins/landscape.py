#
# Copyright (c) 2009 Canonical
#
# Written by Gustavo Niemeyer <gustavo@niemeyer.net>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from ConfigParser import ConfigParser
import os

from smart import sysconf


CLIENT_CONF_PATH = "/etc/landscape/client.conf"


def run():
    if (sysconf.get("use-landscape-proxies", False) and
        os.path.isfile(CLIENT_CONF_PATH)):
        parser = ConfigParser()
        parser.read(CLIENT_CONF_PATH)
        for type in "http", "https", "ftp":
            option = "%s_proxy" % type
            if parser.has_option("client", option) and option not in os.environ:
                setting = parser.get("client", option)
                sysconf.set(option.replace("_", "-"), setting, weak=True)


run()

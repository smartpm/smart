#
# Copyright (c) 2004 Conectiva, Inc.
#
# Written by Gustavo Niemeyer <niemeyer@conectiva.com>
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
from smart import _

kind = "package"

name = _("URPMI Repository")

description = _("""
Repository created for Mandriva's URPMI package manager.
""")

fields = [("baseurl", _("Base URL"), str, None,
           _("Base URL where packages are found under. "
             "Using ' with <hdlurl>' pattern is also supported.")),
          ("directory", _("With directory"), str, "",
           _("Directory path for Base URL")),
          ("hdlurl", _("Header List URL"), str, "",
           _("URL for header list (hdlist or synthesis). If it's hdlist.cz "
             "inside the given base URL, may be left empty. URLs relative "
             "to the Base URL are supported")),
          ("mirrorurl", _("Mirror List URL"), str, "",
           _("URL for mirror list)..."))]

def postParse(data):
    import re
    withre = re.compile("\s+with\s+", re.I)
    if withre.search(data["baseurl"]):
        if "hdlurl" in data:
            raise Error, _("Base URL has 'with', but Header List URL "
                           "was provided")
        tokens = withre.split(data["baseurl"])
        if len(tokens) != 2:
            raise Error, _("Base URL has invalid 'with' pattern")
        data["baseurl"] = tokens[0].strip()
        if tokens[1].strip():
            data["hdlurl"] = tokens[1].strip()
    return data

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

name = _("RPM MetaData")

description = _("""
Repository created with the rpm-metadata project.
""")

fields = [("baseurl", _("Base URL"), str, None,
           _("URL where repodata/ subdirectory is found")),
          ("mirrorlist", _("Mirror list URL"), str, "",
           _("URL which provides list of mirrors for baseurl")),
          ("fingerprint", _("Fingerprint"), str, "",
           _("GPG fingerprint of key signing the channel."))]

def detectLocalChannels(path, media):
    import os
    channels = []
    if os.path.isfile(os.path.join(path, "repodata/repomd.xml")):
        if media:
            baseurl = "localmedia://"
            baseurl += path[len(media.getMountPoint()):]
        else:
            baseurl = "file://"
            baseurl += path
        channel = {"baseurl": str(baseurl)}
        if media:
            infofile = os.path.join(media.getMountPoint(), ".discinfo")
            if os.path.isfile(infofile):
                file = open(infofile)
                skip = file.readline().rstrip()
                name = file.readline().rstrip()
                arch = file.readline().rstrip()
                file.close()
                channel["name"] = "%s - %s - Media" % (name, arch)
        channels.append(channel)
    return channels


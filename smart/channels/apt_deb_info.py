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

name = _("APT-DEB Repository")

description = _("""
Repositories created for APT-DEB.
""")

fields = [("baseurl", _("Base URL"), str, None,
           _("Base URL of repository, where dists/ is located.")),
          ("distribution", _("Distribution"), str, None,
           _("Distribution to use.")),
          ("components", _("Components"), str, "",
           _("Space separated list of components.")),
          ("fingerprint", _("Fingerprint"), str, "",
           _("GPG fingerprint of key signing the channel.")),
          ("keyring", _("Keyring"), str, "",
           _("If provided, channel must necessarily be signed by a key "
             "in the GPG keyring at the given path.")),
          ("trustdb", _("Trustdb"), str, "",
           _("If provided, channel will be checked for a key "
             "in the GPG trust database at the given path."))]

def detectLocalChannels(path, media):
    import os
    channels = []
    distspath = os.path.join(path, "dists")
    if not os.path.isdir(distspath):
        return []
    for dist in [None] + os.listdir(distspath):
        if dist:
            distpath = os.path.join(distspath, dist)
        else:
            distpath = distspath
        if not os.path.isfile(os.path.join(distpath, "Release")):
            continue

        components = {}
        for entry in open(os.path.join(distpath, "Release")):
            if entry.startswith("Components: "):
                entry = entry[12:]
                for component in entry.strip().split(" "):
                    components[component] = True
        for component in components.keys():
            if not os.path.isdir(os.path.join(distpath, component)):
                del components[component]
        if components:
            if media:
                baseurl = "localmedia://"
                baseurl += path[len(media.getMountPoint()):]
            else:
                baseurl = "file://"
                baseurl += path
            components = " ".join(components.keys())
            channel = {"baseurl": baseurl, "components": components}
            if dist:
                channel["distribution"] = dist
            if media:
                infofile = os.path.join(media.getMountPoint(), ".disk/info")
                if os.path.isfile(infofile):
                    file = open(infofile)
                    channel["name"] = file.read().strip()
                    file.close()
            channels.append(channel)
    return channels


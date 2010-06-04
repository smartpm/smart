#
# Copyright (c) 2006 Canonical
#
# Written by Michael Vogt <michael.vogt@ubuntu.com>
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
import posixpath
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import os

# be compatible with 2.3
import sys
if sys.version_info < (2, 4):
    from sets import Set as set

from smart.channel import *
from smart import *


APT_SOURCES_DIR = "/etc/apt/sources.list.d/"
APT_SOURCES = "/etc/apt/sources.list"


def _loadSourcesList(filename):

    keyring_path = sysconf.get("sync-apt-keyring", "/etc/apt/trusted.gpg")
    if not os.path.isfile(keyring_path):
        keyring_path = None
    trustdb_path = sysconf.get("sync-apt-trustdb", "/etc/apt/trustdb.gpg")
    if not os.path.isfile(trustdb_path):
        trustdb_path = None

    file = open(filename)

    # The computed aliases we have seen in the given file.
    seen = set()

    for line in file:
        line = line.strip()

        # We only handle type "deb" or "rpm".
        if not (line.startswith("deb ") or line.startswith("rpm ")):
            continue

        # Strip away in-line comments.
        if "#" in line:
            line = line[:line.find('#')]

        # Split it apart.
        try:
            (type, uri, distro, comps) = line.split(None, 3)
        except ValueError:
            (type, uri, distro) = line.split(None, 2)
            comps = ""

        if uri.startswith("cdrom:"):
            continue # We don't deal with these yet.

        # Build a unique alias.
        m = md5("%s|%s|%s|%s" % (type, uri, distro, comps))
        alias = "aptsync-%s" % m.hexdigest()
        seen.add(alias)

        if type == "deb":
            data = {"type": "apt-deb",
                    "name": "%s - %s" % (distro, comps),
                    "baseurl": uri,
                    "distribution": distro,
                    "components": comps}
        else:
            data = {"type": "apt-rpm",
                    "name": "%s - %s" % (distro, comps),
                    "baseurl": posixpath.join(uri, distro),
                    "components": comps}

        # See if creating a channel works.
        try:
            createChannel(alias, data)
        except Error, e:
            iface.error(_("While using %s: %s") % (file.name, e))
        else:
            # Store it persistently, without destroying existing setttings.
            channel = sysconf.get(("channels", alias))
            if channel is not None:
                channel.update(data)
            else:
                channel = data
                if keyring_path:
                    channel["keyring"] = keyring_path
                if trustdb_path:
                    channel["trustdb"] = trustdb_path
            sysconf.set(("channels", alias), channel)

    file.close()

    return seen


def syncAptChannels(sourcesfile, sourcesdir, force=None):

    # FIXME: Add the fingerprints as well.
    # FIXME: Fix the gpg handling in smart.

    seen = set()

    # First, the sources.list file.
    if os.path.isfile(sourcesfile):
        seen.update(_loadSourcesList(sourcesfile))

    # Then, the sources.list.d directory.
    if os.path.isdir(sourcesdir):
        for entry in os.listdir(sourcesdir):
            if entry.endswith(".list"):
                filepath = os.path.join(sourcesdir, entry)
                if os.path.isfile(filepath):
                    seen.update(_loadSourcesList(filepath))

    # Delete the entries which were not seen in current files.
    channels = sysconf.get("channels")
    for alias in sysconf.keys("channels"):
        if alias.startswith("aptsync-") and alias not in seen:
            sysconf.remove(("channels", alias))


if not sysconf.getReadOnly():
    if sysconf.get("sync-apt-sources",False):
        syncAptChannels(sysconf.get("apt-sources-file", APT_SOURCES),
                        sysconf.get("apt-sources-dir", APT_SOURCES_DIR))

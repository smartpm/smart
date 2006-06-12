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
from smart.channel import *
from smart import *
import os
import md5

APT_SOURCES_DIR = "/etc/apt/sources.list.d/"
APT_SOURCES = "/etc/apt/sources.list"

def _readSourcesList(file):

    # the lines we have seen in the sources.list
    seen = set()
    
    for line in file:
        # we can't handle deb-src yet
        line = line.strip()
        if line.startswith("#") or line.startswith("deb-src") or line == "":
            continue
        # strip away in-line comments
        if "#" in line:
            line = line[:line.find('#')]
        # split it
        try:
            (type, uri, distro, comps) = line.split(None, 3)
        except ValueError:
            (type, uri, distro) = line.split(None, 2)
            comps = ""

        # build a uniq alias
        m = md5.new("%s%s%s%s" % (type, uri, distro,comps))
        alias = "aptsync-%s" % m.hexdigest()
        seen.add(alias)
        data = "[%s]\n" \
               "type=apt-deb\n"\
               "name=%s - %s\n" \
               "baseurl=%s\n"\
               "distribution=%s\n"\
               "components=%s\n" % (alias,distro,comps,uri,distro,comps)
        descriptions = parseChannelsDescription(data)

        # create a channel for the alias
        for alias in descriptions:
            try:
                createChannel(alias, descriptions[alias])
            except Error, e:
                iface.error(_("While using %s: %s") % (file.name, e))
            else:
                sysconf.set(("channels", alias), descriptions[alias])

    # now delete the entries that are no longer in our sources.list
    channels = sysconf.get("channels")
    dellist = filter(lambda al: al.startswith("aptsync-") and al not in seen, channels)
    for d in dellist:
        sysconf.remove(("channels", d))
    
            

def syncAptChannels(sourcesfile, sourcesdir, force=None):

    # FIXME: add the fingerprints as well!
    #        and fix the gpg handling in smart

    # first sources.list
    if os.path.exists(sourcesfile):
        _readSourcesList(open(sourcesfile))

    # then the channels dir
    if os.path.isdir(sourcesdir):

        for entry in os.listdir(sourcesdir):
            if not entry.endswith(".list"):
                continue

            filepath = os.path.join(sourcesdir, entry)
            if not os.path.isfile(filepath):
                continue
            file = open(filepath)
            _readSourcesList(file)



if not sysconf.getReadOnly():
    if sysconf.get("sync-apt-sources",False):
        syncAptChannels(sysconf.get("apt-sources-file", APT_SOURCES),
                        sysconf.get("apt-sources-dir", APT_SOURCES_DIR))


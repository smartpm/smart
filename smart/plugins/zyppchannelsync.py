#
# Written by Jonathan Rocker <linux.learner@gmail.com>
# and Anders F Bjorklund <afb@users.sourceforge.net>
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
import os
import ConfigParser
import re

# be compatible with 2.3
import sys
if sys.version_info < (2, 4):
    from sets import Set as set

from smart.channel import *
from smart import *

ZYPP_REPOS_DIR = "/etc/zypp/repos.d/"

def _getbasearch():
    """
    Get system architecture (like libzypp's ZConfig does it)
    """
    import platform

    architecture = platform.machine()
    if architecture == '':
        return "noarch"
    # some CPUs report i686 but dont implement cx8 and cmov
    # check for both flags in /proc/cpuinfo and downgrade
    # to i586 if either is missing (cf opensuse bug #18885)
    if architecture == "i686":
       if os.path.exists("/proc/cpuinfo"):
           cpuinfo = open("/proc/cpuinfo", "r")
           for line in cpuinfo.readlines():
               if line.startswith("flags"):
                   if line.find("cx8") == -1 or line.find("cmov") == -1:
                       architecture = "i586"
    return architecture

def _getreleasever():
    """
    Get system release and version.
    """
    try:
        import rpm
    except ImportError:
        return None

    releasever = None
    rpmroot = sysconf.get("rpm-root", "/")
    ts = rpm.TransactionSet(rpmroot)
    if ts.openDB() == 0:
        idx = ts.dbMatch('provides', 'openSUSE-release')
        if idx.count() == 0:
            idx = ts.dbMatch('provides', 'distribution-release')
        if idx.count() != 0:
            hdr = idx.next()
            releasever = str(hdr['version'])
            del hdr
        del idx
        del ts
    return releasever

BASEARCH = _getbasearch()
RELEASEVER = _getreleasever()

def _replaceStrings(txt):
    """
    Replace some predefined strings that may appear in the repo file.
    """
    retxt = re.sub("\$basearch", "%s" % BASEARCH, txt)
    retxt = re.sub("\$releasever", "%s" % RELEASEVER, retxt)
    return retxt

def _findBaseUrl(mirrorlist, repo):
    """
    Fetches the first suggested mirror from the mirrorlist and use as baseurl.
    """
    import urllib
    list = urllib.urlopen(mirrorlist)
    baseurl = None
    while 1:
        line = list.readline()
        if line.startswith("#"):
            continue
        elif (line.startswith("http:") or line.startswith("https:") or
            line.startswith("ftp:") or line.startswith("file:")):
            baseurl = line
            break
        elif not line:
            break
    return baseurl

def _loadRepoFile(filename):
    """
    Loads each repository file information.
    """

    file = open(filename)
 
    # The computed aliases we have seen in the given file
    seen = set()

    repofile = ConfigParser.ConfigParser()
    repofile.read(filename)

    for repo in repofile.sections():
        # Iterate through each repo found in file
        alias = "zyppsync-%s" % repo
        name = _replaceStrings(repofile.get(repo, 'name'))
        baseurl = None
        mirrorlist = None

        # Some repos have baseurl, some have mirrorlist
        if repofile.has_option(repo, 'baseurl'):
            baseurl = _replaceStrings(repofile.get(repo, 'baseurl'))
            #baseurl = baseurl.splitlines()[1]
        elif repofile.has_option(repo, 'mirrorlist'):
            mirrorlist = _replaceStrings(repofile.get(repo, 'mirrorlist'))
            baseurl = _findBaseUrl(mirrorlist, repo)
        else:
            iface.warning(_("ZYpp channel %s does not contain baseurl or " \
                            "mirrorlist addresses. Not syncing.") % repo)
            return seen

        if repofile.has_option(repo, 'enabled'):
            enabled = not repofile.getboolean(repo, 'enabled')
        else:
            enabled = False

        if repofile.has_option(repo, 'type'):
            type = repofile.get(repo, 'type')
            if type == "NONE": type = "rpm-md"
        else:
            type = "rpm-md"

        if baseurl.startswith("cd://"):
            baseurl = "localmedia://" + baseurl[6:]
        if baseurl.find("?devices=") > -1:
            baseurl = baseurl.split("?")[0]

        data = {"type": type,
                "name": name,
                "baseurl": baseurl,
                "disabled": enabled}
        if mirrorlist:
            data["mirrorlist"] = mirrorlist
        seen.add(alias)
 
        try:
            createChannel(alias, data)
        except Error, e:
            iface.error(_("While using %s: %s") % (filename, e))
        else:
            # Store it persistently.
            sysconf.set(("channels", alias), data)

    return seen


def syncZyppRepos(reposdir, force=None):
    """
    Sync Smart channels based on ZYpp repositories.
    """

    seen = set()

    if os.path.isdir(reposdir):
        for entry in os.listdir(reposdir):
            if entry.endswith(".repo"):
                filepath = os.path.join(reposdir, entry)
                if os.path.isfile(filepath):
                    seen.update(_loadRepoFile(filepath))

    # Delete the entries which were not seen in current files.
    channels = sysconf.get("channels")
    for alias in sysconf.keys("channels"):
        if alias.startswith("zyppsync-") and alias not in seen:
            sysconf.remove(("channels", alias))


if not sysconf.getReadOnly():
    if sysconf.get("sync-zypp-repos",False):
        syncZyppRepos(sysconf.get("zypp-repos-dir", ZYPP_REPOS_DIR))

# vim:ts=4:sw=4:et
